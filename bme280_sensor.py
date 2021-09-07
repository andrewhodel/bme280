import smbus2
import bme280
import time
import urllib2
import json

req = urllib2.Request("https://dev.ispapp.co:8550/update", headers={"content-type": "application/json"})

port = 1
address = 0x76
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, address)

# the sample method will take a single reading and return a
# compensated_reading object
data = bme280.sample(bus, address, calibration_params)

while True:

    # the compensated_reading class has the following attributes
    print(data.id)
    print(data.timestamp)
    print(data.temperature)
    print(data.pressure)
    print(data.humidity)

    # there is a handy string representation too
    print(data)

    sjson = {"login": "1210_plenum", "key": "asdklhdfga", "collectors": {"ping": [{"host": "temp", "avgRtt": data.temperature, "loss": 0}, {"host": "hum", "avgRtt": data.humidity, "loss": 0}, {"host": "pressure", "avgRtt": data.pressure, "loss": 0}]}}
    json_d = json.dumps(sjson)

    resp = urllib2.urlopen(req, json_d, cafile="/etc/__ispapp_co.ca-bundle").read()

    print(resp)

    time.sleep(10)
