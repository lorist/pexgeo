
import yaml

from json import dumps as json_dumps

from bottle import Bottle, run, request, response
from geoip2 import database as geoip_db
from geoip2 import errors as geoip_error
#

def load_config_file():
    _config_file = open("config.yml", "r").read()
    _config = yaml.load(_config_file)
    return _config

app = Bottle()

""" Config value """
config = load_config_file()

continent_list = {
  "AF": "Africa",
  "AN": "Antarctica",
  "AS": "Asia",
  "EU": "Europe",
  "NA": "North America",
  "OC": "Oceania",
  "SA": "South America"
}

try:
    geoip_reader = geoip_db.Reader(config["maxmind"]["location"])
except geoip_error.GeoIP2Error:
    print("Error : Connection to GeoIP database fail")

""" Default JSON response template """
json_response = { "status": "default",
            "result": {},
            }

""" Application """
@app.route('/policy/v1/participant/location', method='GET')
def send_location_policy():
    params = request.query.decode()
    if "remote_address" in params:
        location_response = json_response
        try:
            continent_code = geoip_reader.country(params.remote_address).continent.code
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
        response.content_type = "application/json"
        return json_dumps(location_response)
    else:
        return """KO"""

run(app, host=config["server"]["bind_address"], port=config["server"]["bind_port"])

""" Database disconnection """
try:
    geoip_reader.close()
except NameError:
    print("Connection to DB not found")

