import smbus2
import bme280
import time
import urllib2
import json
import threading
import platform

start_time = time.time()

# setup configuration
intervalS = 20;
outageIntervalSeconds = 0;
ispapp_key = "asdf"
ispapp_domain = "dev.ispapp.co"
ispapp_port = 8550

port = 1
address = 0x76
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, address)

# create global data object
data = bme280.sample(bus, address, calibration_params)

# create a thread to get data from the bme280 every second
def get_data():

    while True:

        # the sample method will take a single reading and return a
        # compensated_reading object
        data = bme280.sample(bus, address, calibration_params)

        # the compensated_reading class has the following attributes
        #print(data.id)
        #print(data.timestamp)
        #print(data.temperature)
        #print(data.pressure)
        #print(data.humidity)

        # there is a handy string representation too
        #print(data)

        time.sleep(1)

# start the bme280 collection thread
th = threading.Thread(target=get_data)
th.daemon = True
th.start()

# setup url endpoints
ureq = urllib2.Request("https://" + ispapp_domain + ":" + str(ispapp_port) + "/update", headers={"content-type": "application/json"})
creq = urllib2.Request("https://" + ispapp_domain + ":" + str(ispapp_port) + "/config", headers={"content-type": "application/json"})

while True:

    print("\nmaking config request")

    sjson = {"login": "1210_plenum", "key": ispapp_key, "clientInfo": "python2.7 bme280.py", "os": platform.system(), "osVersion": platform.release(), "hardwareMake": "raspberry pi", "hardwareModel": "zero w", "hardwareCpuInfo": platform.machine()}
    json_d = json.dumps(sjson)

    # urllib2.urlopen sends raw text and does not add a trailing newline character
    json_d += "\r\n"

    try:
        resp = urllib2.urlopen(creq, json_d, cafile="/etc/__ispapp_co.ca-bundle").read()
    except:
        print("urllib2.urlopen() reported an error")
        time.sleep(2)
        continue

    r = json.loads(resp)

    if (r.has_key("error")):
        # if there was an error, try again
        time.sleep(2)
        continue

    # valid config request
    #print(r)

    # set intervalS based on server configuration
    outageIntervalSeconds = r["host"]["outageIntervalSeconds"]

    break

while True:

    print("\nmaking update request")

    ut = int(time.time() - start_time)

    # create the request POST json with the bme280 data
    sjson = {"login": "1210_plenum", "key": ispapp_key, "uptime": ut, "collectors": {"ping": [{"host": "temp", "avgRtt": data.temperature, "loss": 0}, {"host": "hum", "avgRtt": data.humidity, "loss": 0}, {"host": "pressure", "avgRtt": data.pressure, "loss": 0}]}}
    json_d = json.dumps(sjson)

    # urllib2.urlopen sends raw text and does not add a trailing newline character
    json_d += "\r\n"

    try:
        resp = urllib2.urlopen(ureq, json_d, cafile="/etc/__ispapp_co.ca-bundle").read()
        print(resp)
    except:
        print("urllib2.urlopen() reported an error")
        time.sleep(2)
        continue

    r = json.loads(resp)

    if (r.has_key("error")):
        # if there was an error, try again
        time.sleep(2)
        continue

    if (r["updateFast"]):
        print("updateFast is True, setting update interval to 2 seconds")
        intervalS = 2
    else:
        # set update wait based on offset, expect 2 seconds for data collection
        intervalS = outageIntervalSeconds - r["lastUpdateOffsetSec"] - 2
        if (intervalS < 2):
            intervalS = 2
        print("updating in " + str(intervalS) + " seconds")

    time.sleep(intervalS)
