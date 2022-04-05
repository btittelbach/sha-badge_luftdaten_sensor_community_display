#!/usr/bin/python3
import ujson
import urequests
import wifi
import badge
import time
import display
import buttons
import system
from collections import namedtuple

sc_pm_sensor_id_ = int(badge.nvs_get_str(
    "sensorcommunity",
    "sid",
    "69759"
))
sc_env_sensor_id_ = sc_pm_sensor_id_ +1
sc_api_url_ = "https://data.sensor.community/airrohr/v1/sensor/{sensorid}/"
sc_update_interval_ = 250

loop_reentrance_avoidance_lock_ = False ## in absence of mutex module

SensorTuple = namedtuple("SensorTuple",("value","unit","trend"))
sensordata_ = {}

weatherfont = "weather42"
weathericons = {
    "arrowup": "\xf0\x58",
    "arrowdown": "\xf0\x44",
    "thermometer": "\xf0\x55",
    "cloud": "\xf0\x41",
    "degree": "\xf0\x42",
    "degC": "\xf0\x3c",
}

usefont = "roboto_regular12"
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
        drawLabel([2, y, display.width()-4, sdh], type_max_width, stype, str(svalue.value)+str(svalue.unit)+" "+str(svalue.trend))
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
        apiConnection.close()
        if len(jsonData) > 1:
            if "sensordatavalues" in jsonData[0]:
                for sdv in jsonData[0]["sensordatavalues"]:
                    unit=""
                    if sdv["value_type"] == "temperature":
                        unit="°C"
                    elif sdv["value_type"] == "pressure" or sdv["value_type"] == "pressure_at_sealevel":
                        unit="Pa"
                    elif sdv["value_type"] == "humidity":
                        unit="%"
                    elif sdv["value_type"] == "P1" or sdv["value_type"] == "P2":
                        unit="ug/m³"
                    sensordata_[sdv["value_type"]] = SensorTuple(value=sdv["value"], unit=unit, trend="")
        if len(jsonData) > 2:
            if "sensordatavalues" in jsonData[-1]:
                for sdv in jsonData[-1]["sensordatavalues"]:
                    if sensordata_[sdv["value_type"]].value > sdv["value"] +1:
                        sensordata_[sdv["value_type"]].trend = fonticons["arrowup"]
                    elif sensordata_[sdv["value_type"]].value < sdv["value"] -1:
                        sensordata_[sdv["value_type"]].trend = fonticons["arrowdown"]

        # except:
        #   print("getSensorData failed")
        #   api_fail_ct_ = api_fail_ct_ +1
        #   if (api_fail_ct_ > 4):
        #       sensordata_ = {} # delete outdated sensordata
    sensordata_["Time"] = SensorTuple(time.strftime("%H:%M  %Y-%m-%d UTC"),"","")

def displayMsg(msg):
    label_h = display.getTextHeight(msg)
    y = display.height()-label_h
    clearRect([0,y,display.width(),label_h])
    display.drawText(0, y, msg, 0, usefont)

def loop():
    global loop_reentrance_avoidance_lock_
    if loop_reentrance_avoidance_lock_:
        return 3
    loop_reentrance_avoidance_lock_ = True
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
    loop_reentrance_avoidance_lock_ = False
    return sc_update_interval_

def buttonExitApp(pressed):
    system.home()

def buttonForceUpdate(pressed):
    displayMsg("updating ...")
    loop()

buttons.attach(buttons.BTN_A, buttonForceUpdate)
buttons.attach(buttons.BTN_B, buttonForceUpdate)
buttons.attach(buttons.BTN_START, buttonExitApp)

displayMsg("getting sensordata from data.sensor.community ...")
while True:
    system.sleep(loop()*1000)
