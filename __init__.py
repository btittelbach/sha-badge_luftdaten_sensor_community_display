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
sc_max_age_ = sc_update_interval_ // 1000 * 3

trend_no_change_range_ = 0.2
trend_history_smooth_factor_ = 0.9

loop_reentrance_avoidance_lock_ = False ## in absence of mutex module

SensorTuple = namedtuple("SensorTuple",("value","trend","ts"))
sensordata_ = {}
trenddata_ = {}

valuefont = "Exo2_Bold22"
unitfont = "Exo2_Thin18"
y_px_offset_between_value_unit_font_ = 6
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

def drawTextReturnWidth(x,y,text,font,scale=1):
    display.drawText(x, y, text, 0, font, scale, scale)
    return display.getTextWidth(text, font) * scale

def draw2Liner(x,y,font,line1,line2):
    display.drawText(x, y, line1, 0, font)
    w1 = display.getTextWidth(line1, font)
    y += display.getTextHeight(line1, font)
    display.drawText(x, y, line2, 0, font)
    w2 = display.getTextWidth(line2, font)
    return max(w1,w2)

def drawDegChar(x, y, char, font, scale):
    # c_height = display.getTextHeight(char, font)*scale
    c_width = display.getTextWidth(char, font)*scale
    r = scale*2
    display.drawCircle(x+r,y+r+7,r,0,360,False,0)
    display.drawText(x+2*r,y,char,0,font,scale,scale)
    return 2*r+c_width

drawPM10 = lambda x,y: draw2Liner(x+2,y+3,unitfont,"PM","10")+2
drawPM2 = lambda x,y: draw2Liner(x+2,y+3,unitfont,"PM","2.5")+2
drawPercent = lambda x,y: drawTextReturnWidth(x, y, "%", unitfont, 2)
# drawDegC = lambda x,y: drawTextReturnWidth(x, y, weathericons["degC"], weatherfont, 1)
drawDegC = lambda x,y: drawDegChar(x, y, "C", unitfont, 2)

def drawData(key, drawunitfunc, row, column):
    rows = 2
    columns = 2
    boxwidth = display.width() // columns
    boxheight = display.height() // rows
    if not key in sensordata_:
        return
    value = "%.1f" % (sensordata_[key].value)
    if sensordata_[key].ts + sc_max_age_ <= time.time():
        value = "??" ## data is too old
    x = boxwidth * column
    y = boxheight * row
    display.drawText(x, y, value, 0, valuefont, 2, 2)
    x += display.getTextWidth(value, valuefont) * 2
    x += drawunitfunc(x, y+y_px_offset_between_value_unit_font_) + 1
    display.drawText(x, y+y_px_offset_between_value_unit_font_, str(sensordata_[key].trend), 0, weatherfont)


def drawLabel(rect, type_max_width, stype, svalue):
    x, y, w, h = rect
    clearRect(rect)
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
    #drawGrid()
    drawData("temperature",drawDegC, 0, 0)
    drawData("humidity",drawPercent, 0, 1)
    drawData("P1",drawPM10, 1, 0)
    drawData("P2",drawPM2, 1, 1)
    # drawData("pressure",..., 2, 0)
    # drawData("pressure_at_sealevel",..., 2, 1)
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
        if len(jsonData) > 0:
            if "sensordatavalues" in jsonData[0]:
                for sdv in jsonData[0]["sensordatavalues"]:
                    sensortype = sdv["value_type"]
                    val = float(sdv["value"])
                    if not sensortype in trenddata_:
                        trenddata_[sensortype] = val
                    trenddata_[sensortype] = trend_history_smooth_factor_*trenddata_[sensortype] + (1.0-trend_history_smooth_factor_)*val
                    change_rel_to_avg = val - trenddata_[sensortype]
                    trend=""
                    if change_rel_to_avg > trend_no_change_range_:
                        trend=weathericons["arrowup"]
                    elif change_rel_to_avg < -1.0*trend_no_change_range_:
                        trend=weathericons["arrowdown"]
                    sensordata_[sensortype] = SensorTuple(value=val, trend=trend, ts=now)


def displayMsg(msg):
    print(msg)
    easydraw.msg(msg)

def loop():
    global loop_reentrance_avoidance_lock_
    if loop_reentrance_avoidance_lock_:
        return 3000
    next_update_in_ms = sc_update_interval_
    try:
        loop_reentrance_avoidance_lock_ = True
        if not wifi.status():
            displayMsg("connecting to WiFi")
            wifi.connect()
        if not wifi.wait(6):
            displayMsg("WiFi wait timed out")
            next_update_in_ms //= 2
        else:
            wifi.ntp()
            #get sensordata
            print("getting data")
            getSensorData([sc_pm_sensor_id_, sc_env_sensor_id_])
            print("printing data")
            printSensorData()
        print("rendering data on epaper")
        ## note: outdated data will not be rendered.
        ##       without wifi, all data may time out and we may render blank screen
        displaySensorDataBetter()
    finally:
        loop_reentrance_avoidance_lock_ = False
        return next_update_in_ms


def buttonExitApp(pressed):
    if pressed:
        return
    system.home()

def buttonForceUpdate(pressed):
    if pressed:
        return
    displayMsg("updating ...")
    loop()

buttons.attach(buttons.BTN_A, buttonForceUpdate)
buttons.attach(buttons.BTN_B, buttonForceUpdate)
buttons.attach(buttons.BTN_START, buttonExitApp)

for x in range(0,2):
    display.drawRect(0, 0, display.width(), display.height(), True, 0xffffff) ## clear display
    display.flush()

displayMsg("getting data from data.sensor.community ...")


virtualtimers.begin(100)
virtualtimers.new(0,loop)
