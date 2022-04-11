#!/usr/bin/python3
import ujson
import urequests
import wifi
import badge
import time
import display
import buttons
import system
import easydraw
import virtualtimers
from collections import namedtuple

sc_pm_sensor_id_ = int(badge.nvs_get_str(
    "sensorcommunity",
    "sid",
    "69759"
))
sc_env_sensor_id_ = sc_pm_sensor_id_ +1
sc_api_url_ = "https://data.sensor.community/airrohr/v1/sensor/{sensorid}/"
sc_update_interval_ = 250000
sc_max_age_ = sc_update_interval_ / 1000 * 3

loop_reentrance_avoidance_lock_ = False ## in absence of mutex module

SensorTuple = namedtuple("SensorTuple",("value","trend","ts"))
sensordata_ = {}

# normfont = "Roboto_Regular12"
# normfont = "Roboto_Black22"
# normfont = "Ocra22"
# normfont = "PermanentMarker36"
# normfont = "Exo2_Bold22"

normfont = "Exo2_Thin18"
weatherfont = "weather42"
weathericons = {
    "arrowup": "\x59", #89
    "arrowdown": "\x45", #69
    "thermometer": "\x56", #86
    "cloud": "\x42", #66
    "degC": "\x3d", #61
}

def clearRect(rect):
    x, y, w, h = rect
    display.drawRect(x, y, w, h, True, 0xffffff)

def drawGrid():
    rows = 2
    columns = 2
    boxwidth = display.width() // columns
    boxheight = display.height() // rows
    for c in range(1,columns):
        display.drawLine(boxwidth*c,0, boxwidth*c, display.height(), 0)
    for r in range(1,rows):
        display.drawLine(0, boxheight*(c), display.width(), boxheight*(c), 0)

def drawData(key, unit, unitfont, scale, row, column):
    rows = 2
    columns = 2
    boxwidth = display.width() // columns
    boxheight = display.height() // rows
    if not key in sensordata_:
        return
    if sensordata_[key].ts + sc_max_age_ <= time.time():
        return ## data is too old, don't display
    x = boxwidth * column
    y = boxheight * row
    value = str(sensordata_[key].value)
    display.drawText(x, y, value, 0, normfont, 2, 2)
    x += display.getTextWidth(value, normfont) * 2
    display.drawText(x, y, unit, 0, unitfont, scale, scale)
    x += display.getTextWidth(unit, unitfont) * scale
    display.drawText(x, y, str(sensordata_[key].trend), 0, weatherfont)


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
        drawLabel([2, y, display.width()-4, sdh], type_max_width, stype, str(svalue.value))
        y += sdh
    display.flush()

def displaySensorDataBetter():
    display.drawRect(0, 0, display.width(), display.height(), True, 0xffffff) ## clear display
    if (len(sensordata_) < 1):
        display.drawText(2, 2, "X", 0, "permanentmarker22", 2, 2)
        display.flush()
        return
    drawGrid()
    drawData("temperature",weathericons["degC"], weatherfont,1, 0, 0)
    drawData("humidity","%", normfont,2, 0, 1)
    drawData("P1"," PM10", normfont,2, 1, 0)
    drawData("P2"," PM2.5", normfont,2, 1, 1)
    # drawData("pressure","Pa", normfont, 2, 0)
    # drawData("pressure_at_sealevel","Pa", normfont, 2, 1)
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
        now = time.time()
        if len(jsonData) > 1:
            if "sensordatavalues" in jsonData[0]:
                for sdv in jsonData[0]["sensordatavalues"]:
                    sensordata_[sdv["value_type"]] = SensorTuple(value=sdv["value"], trend="", ts=now)
        if len(jsonData) > 2:
            if "sensordatavalues" in jsonData[-1]:
                for sdv in jsonData[-1]["sensordatavalues"]:
                    try:
                        if sensordata_[sdv["value_type"]].value > sdv["value"] +1:
                            sensordata_[sdv["value_type"]].trend = weathericons["arrowup"]
                        elif sensordata_[sdv["value_type"]].value < sdv["value"] -1:
                            sensordata_[sdv["value_type"]].trend = weathericons["arrowdown"]
                    except:
                        pass

        # except:
        #   print("getSensorData failed")
        #   api_fail_ct_ = api_fail_ct_ +1
        #   if (api_fail_ct_ > 4):
        #       sensordata_ = {} # delete outdated sensordata
    # sensordata_["Time"] = SensorTuple(time.strftime("%H:%M  %Y-%m-%d UTC"),"")

def displayMsg(msg):
    easydraw.msg(msg)
    # label_h = display.getTextHeight(msg)
    # y = display.height()-label_h
    # clearRect([0,y,display.width(),label_h])
    # display.drawText(0, y, msg, 0, usefont)

def loop():
    global loop_reentrance_avoidance_lock_
    if loop_reentrance_avoidance_lock_:
        return 3000
    loop_reentrance_avoidance_lock_ = True
    if not wifi.status():
        print("connecting to WiFi")
        wifi.connect()
    if not wifi.wait(6):
        print("WiFi wait timed out")
        return 10000

    wifi.ntp()
    #get sensordata
    print("getting data")
    getSensorData([sc_pm_sensor_id_, sc_env_sensor_id_])
    print("printing data")
    printSensorData()
    print("rendering data on epaper")
    displaySensorDataBetter()
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

for x in range(0,2):
    display.drawRect(0, 0, display.width(), display.height(), True, 0xffffff) ## clear display
    display.flush()

displayMsg("getting sensordata from data.sensor.community ...")
# while True:
#     system.sleep(loop())


virtualtimers.begin(100)
virtualtimers.new(0,loop)
