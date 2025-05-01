# Google Takeout Location parser (gtl)
Python 3 script to parse Google Takeout Location JSON files into KML.

## Usage
```bash
usage: gtl.py [-h] [-b BATCH] -i input_file [-k] [-l] [-t TZ] [-x]
              [--date-range DATE_RANGE] [--time-range TIME_RANGE]
              [--top-left TOP_LEFT] [--bottom-right BOTTOM_RIGHT]

Google Takeout Location Parser v3.0

options:
  -h, --help            show this help message and exit
  -b BATCH, --batch BATCH
                        Sets batch size for KML output, default is 2500
  -i input_file, --input input_file
                        JSON file
  -k, --kml             Output a KML file
  -l, --list            List available timezones
  -t TZ, --tz TZ        Select a timezone for output - '<tz_name>'
  -x, --excel           Output an Excel file
  --date-range DATE_RANGE
                        YYYY-MM-DD..YYYY-MM-DD
  --time-range TIME_RANGE
                        HH:MM:SS..HH:MM:SS
  --top-left TOP_LEFT   Top-left coordinate of search grid: lat,long
  --bottom-right BOTTOM_RIGHT
                        Bottom-right coordinate of search grid: lat, long
```
