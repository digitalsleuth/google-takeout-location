# Google Takeout Location parser (gtl)
Python 3 script to parse Google Takeout Location JSON files into KML.

## Usage
```bash
usage: gtl.py [-h] [-d DATE] -i input_file [-k] [-l] [-t TZ] [-x]

Google Takeout Location Parser v3.0

options:
  -h, --help            show this help message and exit
  -d DATE, --date DATE  Specific date to look for - 'YYYY-MM-DD'
  -i input_file, --input input_file
                        JSON file
  -k, --kml             Output a KML file
  -l, --list            List available timezones
  -t TZ, --tz TZ        Select a timezone for output - '<tz_name>'
  -x, --excel           Output an Excel file
```
