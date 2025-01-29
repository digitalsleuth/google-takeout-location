#!/usr/bin/env python3
"""
This script is designed to ingest JSON data from the exported Google Location json file
from a Google Takeout export. When using Google to track your location, this data is saved and
can be exported from your profile.

Only input required is the json file, will export a CSV and a KML file which can be imported into
Google Maps (maps.google.com -> Your Places -> Maps -> Create Map - Import) or Google Earth
https://earth.google.com/web and the PC application.

"""

import json
import os
import sys
import argparse
import csv
from datetime import datetime as dt
from zoneinfo import ZoneInfo, available_timezones
import simplekml

__author__ = "Corey Forman (digitalsleuth)"
__version__ = "2.0"
__date__ = "29 Jan 2025"
__description__ = "Google Takeout Location JSON parser"


def ingest(json_file):
    json_data = open(json_file, "r")
    results = json.load(json_data)
    return results


def generate_kml(filename, all_data):
    """Generates a KML file from the trip data"""
    normal_icon = "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"
    highlight_icon = (
        "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"
    )
    kml = simplekml.Kml()
    for i, this_trip in enumerate(all_data, start=1):
        folder = kml.newfolder()
        trip = folder.newlinestring(name=f"Trip {i}", tessellate=1)
        trip.stylemap.normalstyle.labelstyle.scale = 0
        trip.stylemap.normalstyle.iconstyle.color = "ff3644db"
        trip.stylemap.normalstyle.iconstyle.scale = 1
        trip.stylemap.normalstyle.iconstyle.icon.href = normal_icon
        trip.stylemap.normalstyle.iconstyle.hotspot.x = 32
        trip.stylemap.normalstyle.iconstyle.hotspot.xunits = "pixels"
        trip.stylemap.normalstyle.iconstyle.hotspot.y = 64
        trip.stylemap.normalstyle.iconstyle.hotspot.yunits = "insetPixels"
        trip.stylemap.normalstyle.linestyle.color = "ffff6712"
        trip.stylemap.normalstyle.linestyle.width = 5
        trip.stylemap.highlightstyle.labelstyle.scale = 1
        trip.stylemap.highlightstyle.iconstyle.color = "ff3644db"
        trip.stylemap.highlightstyle.iconstyle.scale = 1
        trip.stylemap.highlightstyle.iconstyle.icon.href = highlight_icon
        trip.stylemap.highlightstyle.iconstyle.hotspot.x = 32
        trip.stylemap.highlightstyle.iconstyle.hotspot.xunits = "pixels"
        trip.stylemap.highlightstyle.iconstyle.hotspot.y = 64
        trip.stylemap.highlightstyle.iconstyle.hotspot.yunits = "insetPixels"
        trip.stylemap.highlightstyle.linestyle.color = simplekml.Color.red
        trip.stylemap.highlightstyle.linestyle.width = 7.5
        this_trip_coords = []
        start_time = this_trip[1]
        end_time = this_trip[8]
        trip.stylemap.highlightstyle.balloonstyle.text = f"""
    <![CDATA[
        <div style="width: 300px;">
            <h2>Trip {i}</h2>
            <p>Starts at {start_time}</p>
            <p>Ends at {end_time}</p>
            <p>Details:</p>
            <p>{' '.join(this_trip[12])}</p>
            <p>Activity / Place: {this_trip[9]}</p>
            <p>Confidence: {this_trip[10]}</p>
        </div>
    ]]>
    """
        trip.stylemap.highlightstyle.balloonstyle.bgcolor = simplekml.Color.white
        trip.stylemap.highlightstyle.balloonstyle.textcolor = simplekml.Color.black
        trip.description = ""
        this_trip_coords.append((this_trip[3], this_trip[2]))
        if this_trip[4]:
            for coord in this_trip[4]:
                this_trip_coords.append((coord[1], coord[0]))
        this_trip_coords.append((this_trip[6], this_trip[5]))
        for coord in this_trip_coords:
            trip.description += f"{coord[0]},{coord[1]}\n"
        coord_len = len(this_trip_coords)
        trip.coords = this_trip_coords
        start_point = folder.newpoint(
            name=f"Start - {start_time} - {this_trip[9]} - Confidence {this_trip[10]} - Source {this_trip[11]}"
        )
        start_point.coords = [this_trip_coords[0]]
        start_point.style.iconstyle.icon.href = (
            "http://maps.google.com/mapfiles/kml/paddle/A.png"
        )
        if coord_len > 2:
            for each in this_trip_coords[1 : coord_len - 1]:
                folder.newpoint(name="Waypoint", coords=[each])
        end_point = folder.newpoint(name=f"End - {end_time}")
        end_point.coords = [this_trip_coords[-1]]
        end_point.style.iconstyle.icon.href = (
            "http://maps.google.com/mapfiles/kml/paddle/B.png"
        )
        folder.name = f"Trip {i} - {start_time} - {end_time} - {this_trip[9]} - {' '.join(this_trip[12])}"
    try:
        kml.save(f"{filename}.kml")
        print(f"KML file generated - {filename}.kml")
    except Exception as err:
        print(f"Error encountered trying to save KML file - {err}")


def parse_json(loaded_json, tz="UTC"):
    parsed_data = []
    for item in loaded_json["timelineObjects"]:
        wpts = []
        pts = []
        detail = []
        probability = None
        if "activitySegment" in item:
            act = item["activitySegment"]
            loc_start_lat = float(act["startLocation"]["latitudeE7"] / 10000000)
            loc_start_long = float(act["startLocation"]["longitudeE7"] / 10000000)
            loc_end_lat = float(act["endLocation"]["latitudeE7"] / 10000000)
            loc_end_long = float(act["endLocation"]["longitudeE7"] / 10000000)
            if (
                "sourceInfo" in act["startLocation"]
                and "sourceInfo" in act["endLocation"]
            ):
                source = f"{act['startLocation']['sourceInfo']}, {act['endLocation']['sourceInfo']}"
            else:
                source = "UNKNOWN - No sourceInfo key"
            start_ms = int(act["duration"]["startTimestampMs"])
            start_time = dt.utcfromtimestamp(
                int(act["duration"]["startTimestampMs"]) / 1000
            )
            end_ms = int(act["duration"]["endTimestampMs"])
            end_time = dt.utcfromtimestamp(
                int(act["duration"]["endTimestampMs"]) / 1000
            )
            if tz != "UTC":
                tz = ZoneInfo(str(tz))
                start_time = start_time.replace(tzinfo=ZoneInfo("UTC"))
                start_time = start_time.astimezone(tz).strftime(
                    f"%Y-%m-%d %H:%M:%S {tz}"
                )
                end_time = end_time.replace(tzinfo=ZoneInfo("UTC"))
                end_time = end_time.astimezone(tz).strftime(f"%Y-%m-%d %H:%M:%S {tz}")
            else:
                start_time = start_time.strftime(f"%Y-%m-%d %H:%M:%S {tz}")
                end_time = end_time.strftime(f"%Y-%m-%d %H:%M:%S {tz}")
            activity_type = act["activityType"]
            if "confidence" in act:
                confidence = act["confidence"].replace("_CONFIDENCE", "")
            else:
                confidence = "UNKNOWN - No confidence key found"
            if "waypointPath" in act:
                waypoints = act["waypointPath"]["waypoints"]
                for waypoint in waypoints:
                    wpts.append(
                        [
                            f"{float(waypoint['latE7'] / 10000000)}",
                            f"{float(waypoint['lngE7'] / 10000000)}",
                        ]
                    )
            if "simplifiedRawPath" in act:
                points = act["simplifiedRawPath"]["points"]
                for point in points:
                    wpts.append(
                        [
                            f"{float(point['latE7'] / 10000000)}",
                            f"{float(point['lngE7'] / 10000000)}",
                        ]
                    )
            if "distance" in act:
                detail.append(f"Distance: {act['distance']}")
            probabilities = act["activities"]
            for odds in probabilities:
                if odds["activityType"] == activity_type:
                    probability = odds["probability"]
                    continue
            if probability:
                detail.append(f"Probability: {probability}")
            else:
                detail.append("Probability: unknown")
            parsed_data.append(
                [
                    start_ms,
                    start_time,
                    loc_start_lat,
                    loc_start_long,
                    wpts,
                    loc_end_lat,
                    loc_end_long,
                    end_ms,
                    end_time,
                    activity_type,
                    confidence,
                    source,
                    detail,
                ]
            )
        if "placeVisit" in item:
            place = item["placeVisit"]
            location = place["location"]
            loc_lat = float(location["latitudeE7"] / 10000000)
            loc_long = float(location["longitudeE7"] / 10000000)
            place_id = location["placeId"]
            address = location["address"]
            loc_name = location["name"]
            detail.append(
                f"Place ID: {place_id} - Address: {address} - Name: {loc_name}"
            )
            if "locationConfidence" in location:
                detail.append(f"Location Confidence: {location['locationConfidence']}")
            if "semanticType" in location:
                loc_type = location["semanticType"].replace("TYPE_", "")
            else:
                loc_type = "NO_LOCATION_TYPE"
            source = location["sourceInfo"]
            start_ms = int(place["duration"]["startTimestampMs"])
            start_time = dt.utcfromtimestamp(
                int(place["duration"]["startTimestampMs"]) / 1000
            )
            end_ms = int(place["duration"]["endTimestampMs"])
            end_time = dt.utcfromtimestamp(
                int(place["duration"]["endTimestampMs"]) / 1000
            )
            if tz != "UTC":
                tz = ZoneInfo(str(tz))
                start_time = start_time.replace(tzinfo=ZoneInfo("UTC"))
                start_time = start_time.astimezone(tz).strftime(
                    f"%Y-%m-%d %H:%M:%S {tz}"
                )
                end_time = end_time.replace(tzinfo=ZoneInfo("UTC"))
                end_time = end_time.astimezone(tz).strftime(f"%Y-%m-%d %H:%M:%S {tz}")
            else:
                start_time = start_time.strftime(f"%Y-%m-%d %H:%M:%S {tz}")
                end_time = end_time.strftime(f"%Y-%m-%d %H:%M:%S {tz}")
            confidence = place["placeConfidence"].replace("_CONFIDENCE", "")
            if "simplifiedRawPath" in place:
                path = place["simplifiedRawPath"]
                for point in path["points"]:
                    pts.append(
                        [
                            f"{float(point['latE7'] / 10000000)}",
                            f"{float(point['lngE7'] / 10000000)}",
                        ]
                    )
            parsed_data.append(
                [
                    start_ms,
                    start_time,
                    loc_lat,
                    loc_long,
                    pts,
                    loc_lat,
                    loc_long,
                    end_ms,
                    end_time,
                    loc_type,
                    confidence,
                    source,
                    detail,
                ]
            )
    return parsed_data


def generate_csv(filename, parsed_data):
    output_file = f"{filename}.csv"
    out_csv = open(output_file, "w", newline="")
    header = [
        "start_epoch",
        "start_time",
        "start_lat",
        "start_long",
        "waypoints",
        "end_lat",
        "end_long",
        "end_epoch",
        "end_time",
        "activity_place_type",
        "confidence",
        "source",
        "detail",
    ]
    try:
        writer = csv.DictWriter(out_csv, header)
        writer.writeheader()
        for trip in parsed_data:
            row = {}
            row["start_epoch"] = trip[0]
            row["start_time"] = trip[1]
            row["start_lat"] = trip[2]
            row["start_long"] = trip[3]
            row["waypoints"] = trip[4]
            row["end_lat"] = trip[5]
            row["end_long"] = trip[6]
            row["end_epoch"] = trip[7]
            row["end_time"] = trip[8]
            row["activity_place_type"] = trip[9]
            row["confidence"] = trip[10]
            row["source"] = trip[11]
            row["detail"] = trip[12]
            writer.writerow(row)
        out_csv.close()
    except Exception as err:
        print(f"Unable to write CSV: {err}")
        sys.exit(1)
    print(f"CSV File {output_file} written successfully")


def print_available_timezones():
    all_tz = []
    for tz in available_timezones():
        all_tz.append(tz)
    tzs = sorted(all_tz)
    for tz in tzs:
        print(tz)


def main():
    """Argument Parsing"""
    arg_parse = argparse.ArgumentParser(
        description=f"Google Takeout Location Parser v{str(__version__)}"
    )
    arg_parse.add_argument("-c", "--csv", help="Output a CSV file", action="store_true")
    arg_parse.add_argument(
        "-i", "--input", metavar="input_file", help="JSON file", required=True
    )
    arg_parse.add_argument("-k", "--kml", help="Output a KML file", action="store_true")
    arg_parse.add_argument(
        "-l", "--list", help="List available timezones", action="store_true"
    )
    arg_parse.add_argument(
        "-t", "--tz", help="Select a timezone for output", type=str, default="UTC"
    )
    if len(sys.argv[1:]) == 0:
        arg_parse.print_help()
        arg_parse.exit()
    if len(sys.argv[1:]) > 0 and ("-l" in sys.argv or "--list" in sys.argv):
        print_available_timezones()
        sys.exit(0)
    args = arg_parse.parse_args()
    if not os.path.exists(args.input) or not os.path.isfile(args.input):
        print(f"Cannot process {args.input}. Please check your path and try again")
        sys.exit(1)
    if args.tz and args.tz not in available_timezones():
        print(
            "Your selected timezone cannot be identified. Please run this script with -l / --list to see the available timezones and try again.\nMake sure you place quotes around the timezone as well."
        )
        sys.exit(1)
    json_content = ingest(args.input)
    parsed_data = parse_json(json_content, args.tz)
    if args.kml:
        generate_kml(args.input, parsed_data)
    if args.csv:
        generate_csv(args.input, parsed_data)


if __name__ == "__main__":
    main()
