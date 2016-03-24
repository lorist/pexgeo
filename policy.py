import argparse
from functools import reduce
import gzip
import json
import requests
import logging
from flask import Flask, g, jsonify, request
import geoip2.database
from geoip2 import errors as geoip_error

DB_FILE_LOCATION = 'data/GeoLite2-Country.mmdb'
DB_FILE_URL = 'http://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz'

continent_list = {
  "AF": "Africa",
  "AN": "Antarctica",
  "AS": "Asia",
  "EU": "Europe",
  "NA": "North America",
  "OC": "Oceania",
  "SA": "South America"
}
""" Default JSON response template """
json_response = { "status": "default",
            "result": {},
            }

app = Flask(__name__)

def setup_logging(loglevel):
    logformat = "%(asctime)s: %(message)s"
    if loglevel:
        logging.basicConfig(level=logging.DEBUG,format=logformat)
    else:
        logging.basicConfig(level=logging.INFO,format=logformat)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Start a the flask server of the geoip project.')
    parser.add_argument('-d','--debug', action='store_true', help='Enable debugging')
    parser.add_argument('-f','--fresh', action='store_true', help='Download a fresh copy of the database')
    parser.add_argument('-o','--download', action='store_true', help='Only download the database - don\'t start the app')
    parser.add_argument("-v", "--verbose", action='store_true', help="increase output verbosity")

    return parser.parse_args()

def download_fresh_db():
    app.logger.info("downloading fresh database from: {}".format(DB_FILE_URL))
    req = requests.get(DB_FILE_URL, stream=True)
    gzip_file_location = "{}.gz".format(DB_FILE_LOCATION)

    with open(gzip_file_location,'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()

    app.logger.info("decompressing database file...")
    with open(DB_FILE_LOCATION, 'wb') as f:
        with gzip.open(gzip_file_location, 'rb') as g:
            f.write(g.read())

def get_db_reader():
    reader = getattr(g, '_db_reader', None)
    if reader is None:
        app.logger.info("opening connection to database")
        reader = geoip2.database.Reader(DB_FILE_LOCATION)
    return reader

""" Application """
@app.route('/policy/v1/participant/location')
def send_location_policy():
    ip = request.args.get('remote_address', '')
    app.logger.warning("Unable find ip address: {}".format(ip))
    if ip:
        location_response = json_response
        geoip_reader = get_db_reader()
        result = geoip_reader.country(ip)
        app.logger.warning("Result: {}".format(result))
        try:
            continent_code = geoip_reader.country(ip).continent.code
            print("User connected from : "+continent_list[continent_code])
            if continent_code == "EU":
                location_response["status"] = "success"
                location_response["result"]["location"] = "AWS-Ireland"
                location_response["result"]["primary_overflow_location"] = "AWS-US-East"
            elif continent_code == "NA" or continent_code == "SA":
                location_response["status"] = "success"
                location_response["result"]["location"] = "AWS-US-East"
                location_response["result"]["primary_overflow_location"] = "AWS-Ireland"
            elif continent_code == "AN" or continent_code == "OC":
                location_response["status"] = "success"
                location_response["result"]["location"] = "AWS-Sydney"
                location_response["result"]["primary_overflow_location"] = "AWS-Singapore"
            elif continent_code == "AS":
                location_response["status"] = "success"
                location_response["result"]["location"] = "AWS-Singapore"
                location_response["result"]["primary_overflow_location"] = "AWS-Sydney"
            else:
                location_response["status"] = "success"
        except geoip_error.AddressNotFoundError:
            print("Dialer IP was not found")
            location_response["status"] = "not found"
        location_response["credit"] = "AWS regional Policy"
        # response.content_type = "application/json"
        # return json_dumps(location_response)
        return jsonify(**location_response)
    else:
        return """KO"""

if __name__ == '__main__':
    args = parse_arguments()
    setup_logging(args.verbose)

    if args.fresh or args.download:
        download_fresh_db()

    if not args.download:
        app.run(debug=args.debug)
