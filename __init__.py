#!/usr/bin/python3
import ujson
import urequests
import wifi
import badge
import time
import display
import buttons
import system
import mutex

sc_pm_sensor_id_ = int(badge.nvs_get_str(
    "sensorcommunity",
    "sid",
    "69759"
))
sc_env_sensor_id_ = sc_pm_sensor_id_ +1
sc_api_url_ = "https://data.sensor.community/airrohr/v1/sensor/{sensorid}/"
sc_update_interval_ = 250

loop_reentrance_avoidance_lock_ = mutex.Mutex()

sensordata_ = {}

weathericons = {
    "arrowup": "\xf0\x58",
    "arrowdown": "\xf0\x44",
    "thermometer": "\xf0\x55",
    "cloud": "\xf0\x41",
    "degree": "\xf0\x42",
    "degC": "\xf0\x3c",
}

usefont = "roboto"
fonticons = {
    "degC":"\x21\x03",
    "arrowup": "\x2b\x4e",
    "arrowdown": "\x2b\x4f"
}

def clearRect(rect):
    x, y, w, h = rect
    display.drawRect(x, y, w, h, True, 0xffffff)

def drawLabel(rect, type_max_width, stype, svalue):
    x, y, w, h = rect
    clearRect(rect)
    # padding = " " * (type_max_width-len(stype))
    # label = "{}:".format(stype, padding, svalue)
    # label_w = display.getTextWidth(label)
    label_h = max([display.getTextHeight(stype), display.getTextHeight(svalue)])
    texty = y + h//2 - label_h//2
    display.drawText(x, texty, stype, 0)
    display.drawText(x+type_max_width+2, texty, ": " + svalue, 0, usefont)
    # display.drawText(x + w//2 - label_w//2, y + h//2 - label_h//2, label, 0)

def printSensorData():
    for stype, svalue in sensordata_.items():
        print("{}: {}".format(stype, svalue))

def displaySensorData():
    if (len(sensordata_) < 1):
        clearRect(0,0,display.width(),display.height())
        display.drawText(2, 2, "X", 0, "permanentmarker22", 2, 2)
        display.flush()
        return
    sdh = (display.height()-2) // len(sensordata_)
    y = 0
    type_max_width = max([ display.getTextWidth(s) for s in sensordata_.keys() ])
    for stype, svalue in sensordata_.items():
        drawLabel([2, y, display.width()-4, sdh], type_max_width, stype, str(svalue))
        y += sdh
    display.flush()

def getSensorData(sids_list):
    for sid in sids_list:
        # try:
        uri = sc_api_url_.format(sensorid=sid)
        apiConnection = urequests.get(url=uri)
        if not apiConnection:
            print("httprequest failed")
            continue
        jsonData = apiConnection.json()
        time.sleep(0.2)
        apiConnection.close()
        for sdv in jsonData[1]["sensordatavalues"]:
            sensordata_[sdv["value_type"]] = sdv["value"]
        # except:
        #   print("getSensorData failed")
        #   api_fail_ct_ = api_fail_ct_ +1
        #   if (api_fail_ct_ > 4):
        #       sensordata_ = {} # delete outdated sensordata
    sensordata_["Time"] = time.strftime("%H:%M  %Y-%m-%d UTC")

def loop():
    if not loop_reentrance_avoidance_lock_.test():
        return 3
    if not wifi.status():
        print("connecting to WiFi")
        wifi.connect()
    if not wifi.wait(6):
        print("WiFi wait timed out")
        return sc_update_interval_ * 4

    wifi.ntp()
    #get sensordata
    print("getting data")
    getSensorData([sc_pm_sensor_id_, sc_env_sensor_id_])
    print("printing data")
    printSensorData()
    print("rendering data on epaper")
    displaySensorData()
    loop_reentrance_avoidance_lock_.release()
    return sc_update_interval_

def buttonExitApp():
    system.home()

button.attach("A", loop)
button.attach("B", loop)
button.attach("START", buttonExitApp)

while True:
    time.sleep(loop())