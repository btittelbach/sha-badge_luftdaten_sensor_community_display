# Sensor.Community E-Paper Data Display

It is a simple app to get data from an AirRohr sensor and display it in a very simple fashion on a Sha2017 e-paper badge.

The app assumes that you have a dustsensor + environmental sensor with two consecutive sensor-ids.

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

- [ ] exit via START button press
- [ ] force update via A/B button press
- [ ] display time of last successfull update
- [ ] larger, easier-to-read text with units instead of json dump
- [ ] maybe a history graph or at least up/down arrow indicating current trend
