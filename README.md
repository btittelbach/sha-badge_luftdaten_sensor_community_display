# Sensor.Community E-Paper Data Display

It is a simple app to get data from an AirRohr sensor and display it in a very simple fashion on a Sha2017 e-paper badge.

The app assumes that you have a dustsensor + environmental sensor with two consecutive sensor-ids.

Pull-Requests welcome. Project is currently evolving on [GitHub](https://github.com/btittelbach/sha-badge_luftdaten_sensor_community_display/)

## configuration

1. connect your badge via USB
2. open the serial console to the badge
3. start the python console
4. set the sensor.community sensor id of airquality-dust-sensor that you want to query:  
   ```
   import badge
   badge.nvs_set_str("sensorcommunity","sid","<YourSensorID>")
   ```  
   you can get the sensor-id from the sensor.community map or by logging in to https://devices.sensor.community/sensors. Click `data` of your sensor and use the particulate matter sensor ID.
5. quit the python console


## Todo

- [x] exit via START button press
- [x] force update via A/B button press
- [x] don't display outdated values
- [x] larger, easier-to-read text with units instead of json dump
- [x] add value subtitle description or make font even larger
- [x] up/down arrow indicating current trend
