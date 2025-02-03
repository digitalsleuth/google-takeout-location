# Google Takeout Location parser (gtl)
Python 3 script to parse Google Takeout Location JSON files into KML.

## Usage
```bash
usage: gtl.py [-h] [-c] [-d DATE] -i input_file [-k] [-l] [-t TZ]

Google Takeout Location Parser v2.3

options:
  -h, --help            show this help message and exit
  -c, --csv             Output a CSV file
  -d DATE, --date DATE  Specific date to look for - 'YYYY-MM-DD'
  -i input_file, --input input_file
                        JSON file
  -k, --kml             Output a KML file
  -l, --list            List available timezones
  -t TZ, --tz TZ        Select a timezone for output - '<tz_name>'
```
