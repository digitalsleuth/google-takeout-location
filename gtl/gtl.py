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
from datetime import datetime as dt, timezone, time
from zoneinfo import ZoneInfo, available_timezones
import pandas as pd
import simplekml

__author__ = "Corey Forman (digitalsleuth)"
__version__ = "3.0"
__date__ = "21 Apr 2025"
__description__ = "Google Takeout Location JSON parser"


def ingest(json_file):
    with open(json_file, "r", encoding="utf-8") as json_data:
        results = json.load(json_data)
    return results


def generate_kml(filename, all_data, fmt, batch, search_grid=None):
    """Generates a KML file from the trip data"""
    normal_icon = "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"
    highlight_icon = (
        "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"
    )
    map_type = None
    batch_size = batch
    if fmt == "timeline":
        map_type = "Trip"
    elif fmt == "locations":
        map_type = "Location"
    kml = simplekml.Kml()
    range_start = None
    range_end = None
    if search_grid:
        bounds = create_search_grid(search_grid[1], search_grid[0])
    else:
        bounds = None
    for i, this_trip in enumerate(all_data, start=1):
        if bounds:
            if fmt == "timeline":
                if not within_search_grid(
                    float(this_trip[2]), float(this_trip[3]), bounds
                ):
                    continue
            elif fmt == "locations":
                if not within_search_grid(
                    float(this_trip[2]), float(this_trip[3]), bounds
                ):
                    continue
        folder = kml.newfolder()
        plot = folder.newlinestring(name=f"{map_type} {i}", tessellate=1)
        plot.stylemap.normalstyle.labelstyle.scale = 0
        plot.stylemap.normalstyle.iconstyle.color = "ff3644db"
        plot.stylemap.normalstyle.iconstyle.scale = 1
        plot.stylemap.normalstyle.iconstyle.icon.href = normal_icon
        plot.stylemap.normalstyle.iconstyle.hotspot.x = 32
        plot.stylemap.normalstyle.iconstyle.hotspot.xunits = "pixels"
        plot.stylemap.normalstyle.iconstyle.hotspot.y = 64
        plot.stylemap.normalstyle.iconstyle.hotspot.yunits = "insetPixels"
        plot.stylemap.normalstyle.linestyle.color = "ffff6712"
        plot.stylemap.normalstyle.linestyle.width = 5
        plot.stylemap.highlightstyle.labelstyle.scale = 1
        plot.stylemap.highlightstyle.iconstyle.color = "ff3644db"
        plot.stylemap.highlightstyle.iconstyle.scale = 1
        plot.stylemap.highlightstyle.iconstyle.icon.href = highlight_icon
        plot.stylemap.highlightstyle.iconstyle.hotspot.x = 32
        plot.stylemap.highlightstyle.iconstyle.hotspot.xunits = "pixels"
        plot.stylemap.highlightstyle.iconstyle.hotspot.y = 64
        plot.stylemap.highlightstyle.iconstyle.hotspot.yunits = "insetPixels"
        plot.stylemap.highlightstyle.linestyle.color = simplekml.Color.red
        plot.stylemap.highlightstyle.linestyle.width = 7.5
        this_trip_coords = []
        if fmt == "timeline":
            start_time = this_trip[1]
            end_time = this_trip[8]
            if range_start is None:
                range_start = start_time.split(" ")[0]
            balloon_text = f"""
    <![CDATA[
        <div style="width: 300px;">
            <h2>Trip {i}</h2>
            <p>Starts at {start_time}</p>
            <p>Ends at {end_time}</p>
            <p>Details:</p>
            <p>{' '.join(this_trip[13])}</p>
            <p>Activity / Place: {this_trip[10]}</p>
            <p>Confidence: {this_trip[11]}</p>
        </div>
    ]]>
    """
            plot.stylemap.highlightstyle.balloonstyle.text = balloon_text
            plot.stylemap.highlightstyle.balloonstyle.bgcolor = simplekml.Color.white
            plot.stylemap.highlightstyle.balloonstyle.textcolor = simplekml.Color.black
            plot.description = ""
            this_trip_coords.append((this_trip[3], this_trip[2]))
            if this_trip[4]:
                for coord in this_trip[4]:
                    this_trip_coords.append((coord[1], coord[0]))
            this_trip_coords.append((this_trip[6], this_trip[5]))
            for coord in this_trip_coords:
                plot.description += f"{coord[0]},{coord[1]}\n"
            coord_len = len(this_trip_coords)
            plot.coords = this_trip_coords
            start_point = folder.newpoint(
                name=f"Start - {start_time} - {this_trip[10]} - Confidence {this_trip[11]} - Source {this_trip[12]}"
            )
            start_point.coords = [this_trip_coords[0]]
            start_point.style.iconstyle.icon.href = (
                "http://maps.google.com/mapfiles/kml/paddle/A.png"
            )
            if coord_len > 2:
                for each in this_trip_coords[1 : coord_len - 1]:
                    wpt_num = this_trip_coords.index(each)
                    folder.newpoint(name=f"Waypoint {wpt_num}", coords=[each])
            end_point = folder.newpoint(name=f"End - {end_time}")
            end_point.coords = [this_trip_coords[-1]]
            end_point.style.iconstyle.icon.href = (
                "http://maps.google.com/mapfiles/kml/paddle/B.png"
            )
            folder.name = f"Trip {i} - {start_time} - {end_time} - {this_trip[10]} - {' '.join(this_trip[13])}"
            if i % batch_size == 0:
                range_end = end_time.split(" ")[0]
                try:
                    kml.save(
                        f"{filename}_{range_start}_{range_end}_{i//batch_size}.kml"
                    )
                    kml = simplekml.Kml()
                    print(
                        f"[+] KML file generated - {filename}_{range_start}_{range_end}_{i//batch_size}.kml"
                    )
                    range_start = None
                    range_end = None
                except Exception as err:
                    print(f"[!] Error encountered trying to save KML file - {err}")
        elif fmt == "locations":
            location_timestamp = this_trip[0]
            if range_start is None:
                range_start = dt.fromisoformat(
                    location_timestamp.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
            if this_trip[8] != "None":
                activity_timestamp = this_trip[8][0][0]
                motion_details = ",".join(this_trip[8][0][1])
            else:
                activity_timestamp = motion_details = this_trip[8]
            balloon_text = f"""
    <![CDATA[
        <div style="width: 300px;">
            <h2>Location {i}</h2>
            <p>Location Timestamp {location_timestamp}</p>
            <p>Details:</p>
            <p>Type / Confidence - {motion_details}</p>
        </div>
    ]]>
    """
            plot.stylemap.highlightstyle.balloonstyle.text = balloon_text
            plot.stylemap.highlightstyle.balloonstyle.bgcolor = simplekml.Color.white
            plot.stylemap.highlightstyle.balloonstyle.textcolor = simplekml.Color.black
            plot.description = ""
            this_trip_coords.append((this_trip[3], this_trip[2]))
            for coord in this_trip_coords:
                plot.description += f"{coord[0]},{coord[1]}\n"
            plot.coords = this_trip_coords
            plot_point = folder.newpoint(name=f"{map_type} {i} - {location_timestamp}")
            plot_point.coords = [this_trip_coords[0]]
            plot_point.style.iconstyle.icon.href = (
                "http://maps.google.com/mapfiles/kml/paddle/blu-blank.png"
            )
            folder.name = f"{map_type} {i} - {location_timestamp}/{activity_timestamp} - Accuracy {this_trip[4]} - Type (T) / Confidence (C) {motion_details} - Source {this_trip[5]}"
            if i % batch_size == 0:
                range_end = dt.fromisoformat(
                    location_timestamp.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d")
                try:
                    kml.save(
                        f"{filename}_{range_start}_{range_end}_{i//batch_size}.kml"
                    )
                    print(
                        f"[+] KML file generated - {filename}_{range_start}_{range_end}_{i//batch_size}.kml"
                    )
                    kml = simplekml.Kml()
                    range_start = None
                    range_end = None
                except Exception as err:
                    print(f"[!] Error encountered trying to save KML file - {err}")
    if len(kml.features) > 0:
        if not range_end:
            filename = f"{filename}_{range_start}_final.kml"
        else:
            filename = f"{filename}_{range_start}_{range_end}_final.kml"
        try:
            kml.save(f"{filename}")
            print(f"[+] KML file generated - {filename}")
        except Exception as err:
            print(f"[!] Error encountered trying to save KML file - {err}")


def get_timeline_objects(loaded_json, tz="UTC", date_range=None, time_range=None):
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
            start_time = dt.fromtimestamp(
                int(act["duration"]["startTimestampMs"]) / 1000, timezone.utc
            )
            end_ms = int(act["duration"]["endTimestampMs"])
            end_time = dt.fromtimestamp(
                int(act["duration"]["endTimestampMs"]) / 1000, timezone.utc
            )
            if tz != "UTC":
                tz = ZoneInfo(str(tz))
                start_time = start_time.replace(tzinfo=timezone.utc)
                start_time = start_time.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
                end_time = end_time.replace(tzinfo=timezone.utc)
                end_time = end_time.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            else:
                start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
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
            if date_range and time_range:
                start_date_in_scope, start_time_in_scope = date_filter(
                    start_time, date_range, time_range, tz
                )
                end_date_in_scope, end_time_in_scope = date_filter(
                    end_time, date_range, time_range, tz
                )
                if not (
                    (start_date_in_scope and start_time_in_scope)
                    or (end_date_in_scope and end_time_in_scope)
                ):
                    continue
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
                    tz,
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
            start_time = dt.fromtimestamp(
                int(place["duration"]["startTimestampMs"]) / 1000, timezone.utc
            )
            end_ms = int(place["duration"]["endTimestampMs"])
            end_time = dt.fromtimestamp(
                int(place["duration"]["endTimestampMs"]) / 1000, timezone.utc
            )
            if tz != "UTC":
                tz = ZoneInfo(str(tz))
                start_time = start_time.replace(tzinfo=timezone.utc)
                start_time = start_time.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
                end_time = end_time.replace(tzinfo=timezone.utc)
                end_time = end_time.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
            else:
                start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
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
            if date_range or time_range:
                start_date_in_scope, start_time_in_scope = date_filter(
                    start_time, date_range, time_range, tz
                )
                end_date_in_scope, end_time_in_scope = date_filter(
                    end_time, date_range, time_range, tz
                )
                if not (
                    (start_date_in_scope and start_time_in_scope)
                    or (end_date_in_scope and end_time_in_scope)
                ):
                    continue
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
                    tz,
                    loc_type,
                    confidence,
                    source,
                    detail,
                ]
            )
    return parsed_data


def get_locations(loaded_json, tz="UTC", date_range=None, time_range=None):
    parsed_data = []
    for location in loaded_json["locations"]:
        locLat = float(location["latitudeE7"] / 10000000)
        locLong = float(location["longitudeE7"] / 10000000)
        locAccuracy = location["accuracy"]
        source = location["source"]
        deviceTag = location["deviceTag"]
        if "deviceDesignation" in location:
            deviceDesignation = location["deviceDesignation"]
        else:
            deviceDesignation = "None"
        timestamp = dt.fromisoformat(location["timestamp"]).isoformat(
            timespec="milliseconds"
        )
        if tz != "UTC":
            tz = ZoneInfo(str(tz))
            timestamp = dt.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
            timestamp = timestamp.astimezone(tz).isoformat(timespec="milliseconds")
        if date_range or time_range:
            date_in_scope, time_in_scope = date_filter(
                timestamp, date_range, time_range, tz
            )
            if not (date_in_scope and time_in_scope):
                continue
        activity_details = []
        motion_details = []
        if "activity" in location:
            activities = location["activity"]
            for each_activity in activities:
                activity = each_activity["activity"]
                activity_timestamp = each_activity["timestamp"]
                if tz != "UTC":
                    tz = ZoneInfo(str(tz))
                    activity_timestamp = dt.fromisoformat(activity_timestamp).replace(
                        tzinfo=timezone.utc
                    )
                    activity_timestamp = activity_timestamp.astimezone(tz).isoformat(
                        timespec="milliseconds"
                    )
                for motion in activity:
                    motion_type = motion["type"]
                    motion_confidence = motion["confidence"]
                    motion_details.append(f"T:{motion_type}-C:{motion_confidence}")
            activity_details.append([activity_timestamp, motion_details])
        if not activity_details:
            activity_details = "None"

        parsed_data.append(
            [
                timestamp,
                tz,
                locLat,
                locLong,
                locAccuracy,
                source,
                deviceTag,
                deviceDesignation,
                activity_details,
            ]
        )
    sorted_data = sorted(parsed_data, key=lambda row: dt.fromisoformat(row[0]))
    return sorted_data


def parse_json(loaded_json, tz="UTC", date_range=None, time_range=None):
    if "timelineObjects" in loaded_json:
        parsed_data = get_timeline_objects(
            loaded_json, tz=tz, date_range=date_range, time_range=time_range
        )
        fmt = "timeline"
    elif "locations" in loaded_json:
        parsed_data = get_locations(
            loaded_json, tz=tz, date_range=date_range, time_range=time_range
        )
        fmt = "locations"
    else:
        print("[!] Unable to find 'timelineObjects' or 'locations' in the JSON file.")
        sys.exit(1)
    return parsed_data, fmt


def generate_excel(filename, parsed_data, fmt):
    if fmt == "timeline":
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
            "timezone",
            "activity_place_type",
            "confidence",
            "source",
            "detail",
        ]
        output_worksheet = []
        output_worksheet = (
            {k: [] for k in header} if not output_worksheet else output_worksheet
        )
        output_file = f"{filename}.xlsx"
        for trip in parsed_data:
            output_worksheet["start_epoch"].append(trip[0])
            output_worksheet["start_time"].append(trip[1])
            output_worksheet["start_lat"].append(trip[2])
            output_worksheet["start_long"].append(trip[3])
            output_worksheet["waypoints"].append(trip[4])
            output_worksheet["end_lat"].append(trip[5])
            output_worksheet["end_long"].append(trip[6])
            output_worksheet["end_epoch"].append(trip[7])
            output_worksheet["end_time"].append(trip[8])
            output_worksheet["timezone"].append(trip[9])
            output_worksheet["activity_place_type"].append(trip[10])
            output_worksheet["confidence"].append(trip[11])
            output_worksheet["source"].append(trip[12])
            output_worksheet["detail"].append(trip[13])
        with pd.ExcelWriter(path=output_file, engine="xlsxwriter", mode="w") as writer:
            try:
                chunked_data = chunk_list(output_worksheet, "Locations")
                for chunk_dict, sheet_name in chunked_data:
                    location_chunk = pd.DataFrame(data=chunk_dict)
                    if not location_chunk.empty:
                        location_chunk.to_excel(
                            excel_writer=writer, sheet_name=sheet_name, index=False
                        )
                        worksheet = writer.sheets[sheet_name]
                        (max_row, max_col) = location_chunk.shape
                        worksheet.set_column(0, 1, 50)
                        worksheet.set_column(2, max_col - 1, 30)
                        worksheet.autofilter(0, 0, max_row, max_col - 1)
            except Exception as err:
                print(f"[!] Unable to write Excel: {err}")
                sys.exit(1)
    elif fmt == "locations":
        header = [
            "timestamp",
            "timezone",
            "latitude",
            "longitude",
            "accuracy",
            "source",
            "deviceTag",
            "deviceDesignation",
            "activity_timestamp",
            "motions",
        ]
        output_worksheet = []
        output_worksheet = (
            {k: [] for k in header} if not output_worksheet else output_worksheet
        )
        output_file = f"{filename}.xlsx"
        for trip in parsed_data:
            output_worksheet["timestamp"].append(trip[0])
            output_worksheet["timezone"].append(trip[1])
            output_worksheet["latitude"].append(trip[2])
            output_worksheet["longitude"].append(trip[3])
            output_worksheet["accuracy"].append(trip[4])
            output_worksheet["source"].append(trip[5])
            output_worksheet["deviceTag"].append(trip[6])
            output_worksheet["deviceDesignation"].append(trip[7])
            if trip[8] != "None":
                output_worksheet["activity_timestamp"].append(trip[8][0][0])
                output_worksheet["motions"].append("|".join(trip[8][0][1]))
            else:
                output_worksheet["activity_timestamp"].append("None")
                output_worksheet["motions"].append("None")
        with pd.ExcelWriter(path=output_file, engine="xlsxwriter", mode="w") as writer:
            try:
                chunked_data = chunk_list(output_worksheet, "locations")
                for chunk_dict, sheet_name in chunked_data:
                    location_chunk = pd.DataFrame(data=chunk_dict)
                    if not location_chunk.empty:
                        location_chunk.to_excel(
                            excel_writer=writer, sheet_name=sheet_name, index=False
                        )
                        worksheet = writer.sheets[sheet_name]
            except Exception as err:
                print(f"[!] Unable to write Excel: {err}")
                sys.exit(1)
    print(f"[+] Excel file generated - {output_file}")


def create_search_grid(coord1, coord2):
    lat1, long1 = coord1
    lat2, long2 = coord2

    return (
        min(lat1, lat2),
        max(lat1, lat2),
        min(long1, long2),
        max(long1, long2),
    )


def within_search_grid(lat, long, bounds):
    min_lat, max_lat, min_long, max_long = bounds
    return min_lat <= lat <= max_lat and min_long <= long <= max_long


def chunk_list(sheet_dict, sheet_name):
    chunks = []
    if "latitude" in sheet_dict and len(sheet_dict["latitude"]) > 1000000:
        list_len = len(sheet_dict["latitude"])
        chunk_size = 1000000

        for start in range(0, list_len, chunk_size):
            end = min(start + chunk_size, list_len)
            chunk_dict = {
                key: value[start:end] if isinstance(value, list) else value
                for key, value in sheet_dict.items()
            }
            chunks.append((chunk_dict, f"{sheet_name}_{len(chunks) + 1}"))
    else:
        chunks.append((sheet_dict, sheet_name))
    return chunks


def print_available_timezones():
    all_tz = []
    for tz in available_timezones():
        all_tz.append(tz)
    tzs = sorted(all_tz)
    for tz in tzs:
        print(tz)


def date_filter(timestamp, date_range, time_range, tz="UTC"):
    date_scope = False
    time_scope = False
    tz_obj = ZoneInfo(str(tz))
    dt_obj = dt.fromisoformat(timestamp).astimezone(tz_obj)
    if date_range:
        start_date, end_date = date_range.split("..")
        s_date = dt.fromisoformat(start_date).astimezone(tz_obj).date()
        e_date = dt.fromisoformat(end_date).astimezone(tz_obj).date()
        if s_date <= dt_obj.date() <= e_date:
            date_scope = True
    if time_range:
        start_time, end_time = time_range.split("..")
        s_time = time.fromisoformat(start_time)
        e_time = time.fromisoformat(end_time)
        if s_time <= dt_obj.time() <= e_time:
            time_scope = True

    return date_scope, time_scope


def parse_coord(s):
    try:
        lat_str, long_str = s.split(",")
        return float(lat_str), float(long_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Coordinates must be in format: lat,long"
        ) from exc


def main():
    arg_parse = argparse.ArgumentParser(
        description=f"Google Takeout Location Parser v{str(__version__)}"
    )
    arg_parse.add_argument(
        "-b",
        "--batch",
        help="Sets batch size for KML output, default is 2500",
        type=int,
        default=2500,
    )
    arg_parse.add_argument(
        "-i", "--input", metavar="input_file", help="JSON file", required=True
    )
    arg_parse.add_argument("-k", "--kml", help="Output a KML file", action="store_true")
    arg_parse.add_argument(
        "-l", "--list", help="List available timezones", action="store_true"
    )
    arg_parse.add_argument(
        "-t",
        "--tz",
        help="Select a timezone for output - '<tz_name>'",
        type=str,
        default="UTC",
    )
    arg_parse.add_argument(
        "-x", "--excel", help="Output an Excel file", action="store_true"
    )
    arg_parse.add_argument("--date-range", help="YYYY-MM-DD..YYYY-MM-DD")
    arg_parse.add_argument("--time-range", help="HH:MM:SS..HH:MM:SS")
    arg_parse.add_argument(
        "--top-left",
        type=parse_coord,
        help="Top-left coordinate of search grid: lat,long",
    )
    arg_parse.add_argument(
        "--bottom-right",
        type=parse_coord,
        help="Bottom-right coordinate of search grid: lat, long",
    )
    if len(sys.argv[1:]) == 0:
        arg_parse.print_help()
        arg_parse.exit()
    if len(sys.argv[1:]) > 0 and ("-l" in sys.argv or "--list" in sys.argv):
        print_available_timezones()
        sys.exit(0)
    args = arg_parse.parse_args()
    filename = args.input
    if not os.path.exists(filename) or not os.path.isfile(filename):
        print(f"[!] Cannot process {filename}. Please check your path and try again")
        sys.exit(1)
    if args.tz and args.tz not in available_timezones():
        print(
            "[!] Your selected timezone cannot be identified. Please run this script with -l / --list to see the available timezones and try again."
        )
        sys.exit(1)
    if args.top_left and args.bottom_right:
        search_grid = [args.top_left, args.bottom_right]
        print(
            f"[-] Creating a search grid between {args.top_left} and {args.bottom_right}"
        )
    else:
        search_grid = None
    if args.date_range and args.time_range:
        if ".." not in args.date_range or ".." not in args.time_range:
            print(
                "[!] Make sure your date range is YYYY-MM-DD..YYYY-MM-DD and your time range is HH:MM:SS..HH:MM:SS and surround each range with quotes"
            )
            sys.exit(1)
        print(
            f"[-] Filtering on dates {args.date_range.split('..')[0]} and {args.date_range.split('..')[1]}"
        )
        print(
            f"[-] Filtering on times {args.time_range.split('..')[0]} and {args.time_range.split('..')[1]}"
        )
        filename = f"{filename}-{args.date_range}"    
    print(f"[-] Ingesting {filename}")
    json_content = ingest(filename)
    print("[-] Parsing json content")

    parsed_data, fmt = parse_json(
        json_content, args.tz, args.date_range, args.time_range
    )
    if args.kml:
        print(
            "[-] Generating KML file. This can take a long time for large datasets. Please be patient."
        )
        print(f"[-] Started KML generation at {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
        generate_kml(filename, parsed_data, fmt, args.batch, search_grid)
        print(
            f"[+] Finished KML generation at {dt.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    if args.excel:
        print(
            "[-] Generating Excel file. This can take a long time for large datasets. Please be patient."
        )
        print(f"[-] Started Excel generation at {dt.now()}")
        generate_excel(filename, parsed_data, fmt)
        print(f"[+] Finished Excel generation at {dt.now()}")


if __name__ == "__main__":
    main()
