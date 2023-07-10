import smbus2
import bme280
import time
import json
import threading
import platform
import os
import socket
import ssl

# setup configuration
intervalS = 20
outageIntervalSeconds = 0
updateIntervaSeconds = 0
ispapp_login = "aaaa"
ispapp_key = "aaaaaa"
ispapp_domain = "subdomain.ispapp.co"
ispapp_port = 8550

port = 1
address = 0x76
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, address)

# create global data object
data = bme280.sample(bus, address, calibration_params)

# create a thread to get data from the bme280 every second
def get_data():

    global data

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
context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_default_certs()
context.load_verify_locations(cafile="/etc/__ispapp_co.ca-bundle")

while True:

    print("\nmaking config request")

    sjson = {"clientInfo": "python2.7 bme280.py", "os": platform.system(), "osVersion": platform.release(), "hardwareMake": "raspberry pi", "hardwareModel": "zero w", "hardwareCpuInfo": platform.machine(), "webshellSupport": False, "firmwareUpgradeSupport": False, "bandwidthTestSupport": False}
    json_d = json.dumps(sjson)

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = context.wrap_socket(s, server_hostname=ispapp_domain)
        ssl_sock.connect((ispapp_domain, ispapp_port))

        print(json_d)

        ssl_sock.write("POST /config?login=" + ispapp_login + "&key=" + ispapp_key + " HTTP/1.1\r\nHost: " + ispapp_domain + ":" + str(ispapp_domain) + "\r\nConnection: keep-alive\r\nContent-Type: application/json\r\nContent-Length: " + str(len(json_d)) + "\r\n\r\n" + json_d + "\r\n\r\n")

        resp = b''
        while (True):
            chunk = ssl_sock.recv(1024)
            resp += chunk
            if (len(chunk) < 1024):
                break

        #print(resp)

        ssl_sock.close()

        head = resp.split("\r\n\r\n", 1)
        resp = head[1]
        head = head[0]

        r = json.loads(resp)

        if (r.has_key("error")):
            # if there was an error, try again
            time.sleep(2)
            continue

        # valid config request
        #print(r)

        # store intervals
        outageIntervalSeconds = r["host"]["outageIntervalSeconds"]
        updateIntervalSeconds = r["host"]["updateIntervalSeconds"]

    except Exception as e:
        print("error", e)
        time.sleep(2)
        continue

    break

while True:

    print("\nmaking update request")

    # create the request POST json with the bme280 data
    sjson = {"uptime": int(os.times()[4]), "collectors": {"sensor": {"env": [{"name": "BME280 Environment Sensor", "temp": data.temperature, "humidity": data.humidity, "pressure": data.pressure}]}}}
    json_d = json.dumps(sjson)

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = context.wrap_socket(s, server_hostname=ispapp_domain)
        ssl_sock.connect((ispapp_domain, ispapp_port))

        #print(json_d)

        ssl_sock.write("POST /update?login=" + ispapp_login + "&key=" + ispapp_key + " HTTP/1.1\r\nHost: " + ispapp_domain + ":" + str(ispapp_domain) + "\r\nConnection: keep-alive\r\nContent-Type: application/json\r\nContent-Length: " + str(len(json_d)) + "\r\n\r\n" + json_d + "\r\n\r\n")

        resp = b''
        while (True):
            chunk = ssl_sock.recv(1024)
            resp += chunk
            if (len(chunk) < 1024):
                break

        #print(resp)

        ssl_sock.close()

        head = resp.split("\r\n\r\n", 1)
        resp = head[1]
        head = head[0]

        r = json.loads(resp)

        #print(r)

        if (r.has_key("error")):
            # if there was an error, try again
            time.sleep(2)
            continue

        if (r["updateFast"]):
            print("updateFast is True, setting update interval to 2 seconds")
            intervalS = 2
        else:
            # set update interval from outage update and offset
            intervalS = outageIntervalSeconds - r["lastUpdateOffsetSec"]

            if (updateIntervalSeconds - r["lastColUpdateOffsetSec"] <= intervalS + 5):
                # the next update response is within this update response plus request response time (5 seconds max, on planet)
                # set update interval from collector update and offset
                intervalS = updateIntervalSeconds - r["lastColUpdateOffsetSec"]

            print("updating in " + str(intervalS) + " seconds")

    except Exception as e:
        print("/update error", e)
        time.sleep(2)
        continue

    time.sleep(intervalS)
