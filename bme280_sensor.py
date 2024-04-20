import smbus2
import bme280
import time
import json
import threading
import platform
import os
import socket
import ssl
import subprocess
import getopt
import sys
import random

# setup configuration
intervalS = 20
outageIntervalSeconds = 0
updateIntervaSeconds = 0
ispapp_login = "aaaaaa"
ispapp_key = "aaaaa"
ispapp_domain = "monitor.xyzbots.com"
ispapp_port = 8550

print("Usage: python3 bme280.py --domain=domain --port=port --login=login --key=key")

opts, args = getopt.getopt(sys.argv[1:], "", ["domain=", "port=", "login=", "key="])

for o, a in opts:

    if (o == "--domain"):
        ispapp_domain = a
    elif (o == "--port"):
        ispapp_port = int(a)
    elif (o == "--login"):
        ispapp_login = a
    elif (o == "--key"):
        ispapp_key = a

port = 1
address = 0x76
bus = smbus2.SMBus(port)

# create a thread to get data from the bme280 every second
def get_data():

    global data

    while True:

        time.sleep(1)

        if (data == None):
            try:
                # try to calibrate again
                calibration_params = bme280.load_calibration_params(bus, address)
            except Exception as e:
                # could not calibrate
                data = None
                continue

        # the sample method will take a single reading and return a
        # compensated_reading object
        try:
            data = bme280.sample(bus, address, calibration_params)
        except Exception as e:
            # set data to None to not send invalid data
            data = None
            continue

        # the compensated_reading class has the following attributes
        #print(data.id)
        #print(data.timestamp)
        #print(data.temperature)
        #print(data.pressure)
        #print(data.humidity)

        # there is a handy string representation too
        #print(data)

try:

    calibration_params = bme280.load_calibration_params(bus, address)

    # create global data object
    data = bme280.sample(bus, address, calibration_params)

    # start the bme280 collection thread
    th = threading.Thread(target=get_data)
    th.daemon = True
    th.start()

except Exception as e:
    print("no bme280 sensor found")
    data = None

# setup url endpoints
context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_default_certs()
context.load_verify_locations(cafile="/home/pi/ca-bundle.ca-bundle")

while True:

    print("\nmaking config request")

    sjson = {"clientInfo": "python2.7 bme280.py", "os": platform.system(), "osVersion": platform.release(), "hardwareMake": "raspberry pi", "hardwareModel": "zero w", "hardwareCpuInfo": platform.machine(), "webshellSupport": False, "firmwareUpgradeSupport": False, "bandwidthTestSupport": False}
    json_d = json.dumps(sjson)

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = context.wrap_socket(s, server_hostname=ispapp_domain)
        ssl_sock.connect((ispapp_domain, ispapp_port))

        ssl_sock.send(bytes("POST /config?login=" + ispapp_login + "&key=" + ispapp_key + " HTTP/1.1\r\nHost: " + ispapp_domain + ":" + str(ispapp_domain) + "\r\nConnection: keep-alive\r\nContent-Type: application/json\r\nContent-Length: " + str(len(json_d)) + "\r\n\r\n" + json_d + "\r\n\r\n", "utf-8"))

        resp = b""
        while (True):
            chunk = ssl_sock.recv(1024)
            resp += chunk
            if (len(chunk) < 1024):
                break

        ssl_sock.close()

        head = resp.split(bytes("\r\n\r\n", "utf-8"), 1)

        resp = head[1]
        head = head[0]

        r = json.loads(resp)

        #print(r)

        if ("error" in r):
            # if there was an error, try again
            print("error", r["error"])
            time.sleep(2)
            continue

        # valid config request

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

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = context.wrap_socket(s, server_hostname=ispapp_domain)
        ssl_sock.connect((ispapp_domain, ispapp_port))

        # get IP address
        ipinfo = subprocess.check_output(["/sbin/ifconfig"])
        routeinfo = subprocess.check_output(["/sbin/route", "-n"])
        ipaddr = ""
        wan_interface = ""

        route_lines = routeinfo.splitlines()
        for r in route_lines:
            try:
                # IPv4
                if (r.index("0.0.0.0") == 0):
                        try:
                            p = r.split()
                            wan_interface = p[-1]
                        except Exception as e:
                            pass
            except Exception as e:
                pass

        if (wan_interface != ""):
                #print("wan interface", wan_interface)
                ifconfig_lines = ipinfo.splitlines()
                index = 0
                for l in ifconfig_lines:
                    try:
                        if (l.index(wan_interface) == 0):
                            # next line has IP address
                            try:
                                p = ifconfig_lines[index+1].split()
                                ipaddr = p[1]
                            except Exception as e:
                                pass
                    except Exception as e:
                        pass
                    index += 1

        #print(ipaddr)

        # create random length string
        random_length = random.randrange(800)
        random_string = ""
        r = 0
        while (r < random_length):
            random_string += "0"
            r += 1

        # create the request POST json with the bme280 data
        if (data == None):
            sjson = {"uptime": int(os.times()[4]), "collectors": {}, "wanIp": ipaddr, "random": random_string}
        else:
            sjson = {"uptime": int(os.times()[4]), "collectors": {"sensor": {"env": [{"name": "BME280 Environment Sensor", "temp": data.temperature, "humidity": data.humidity, "pressure": data.pressure}]}}, "wanIp": ipaddr, "random": random_string}
        json_d = json.dumps(sjson)

        #print(json_d)

        ssl_sock.send(bytes("POST /update?login=" + ispapp_login + "&key=" + ispapp_key + " HTTP/1.1\r\nHost: " + ispapp_domain + ":" + str(ispapp_domain) + "\r\nConnection: keep-alive\r\nContent-Type: application/json\r\nContent-Length: " + str(len(json_d)) + "\r\n\r\n" + json_d + "\r\n\r\n", "utf-8"))

        resp = b""
        while (True):
            chunk = ssl_sock.recv(1024)
            resp += chunk
            if (len(chunk) < 1024):
                break

        #print(resp)

        ssl_sock.close()

        head = resp.split(bytes("\r\n\r\n", "utf-8"), 1)
        resp = head[1]
        head = head[0]

        r = json.loads(resp)

        print(r)

        if ("error" in r):
            # if there was an error, try again
            print("error", r["error"])
            time.sleep(2)
            continue

        if (r["updateFast"]):
            print("updateFast is True, setting update interval to 2 seconds")
            intervalS = 2
        else:
            # update using the outage update wait
            intervalS = outageIntervalSeconds - r["lastUpdateOffsetSec"]

            if (updateIntervalSeconds - r["lastColUpdateOffsetSec"] <= intervalS):
                # update using the col update wait
                intervalS = updateIntervalSeconds - r["lastColUpdateOffsetSec"]

        if (type(intervalS) != int):
            # invalid interval
            intervalS = 2

        print("updating in " + str(intervalS) + " seconds")

    except Exception as e:
        print("/update error", e)
        intervalS = 2

    if (intervalS < 0):
        # time.sleep() does not accept a negative number
        intervalS = 0

    time.sleep(intervalS)
