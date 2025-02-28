**Future Fish AgroTech Mobile App**
_See: app.futuregishagro.com_

Generate Dummy db data
python manage.py generate_dummy_sensor_data 2  # Generate 60 days of data for pond ID 2
python manage.py generate_dummy_sensor_data 2 --clear  # Clear existing data first
python manage.py generate_dummy_sensor_data 2 --days 30  # Generate 30 days of data

MQTT Topics
Control Topics:
futurefish/ponds/{pond_id}/control/feed
futurefish/ponds/{pond_id}/control/water
futurefish/ponds/{pond_id}/automation/feed
futurefish/ponds/{pond_id}/automation/water

Status Topics:
futurefish/ponds/{pond_id}/status/feed
futurefish/ponds/{pond_id}/status/water
futurefish/ponds/{pond_id}/status/automation

Sensor topic:
futurefish/ponds/{pond_id}/sensors

To-Do:
1. Send Automation Commands (Feed/Water):
    - Prevent repetitive feeding i.e do not allow feeding until ongoing operation is complete
    - ESP32 feedback mechanism (status report) on control commands before creating DeviceLog
    - Asynchronous operation
    - Scheduling (cron jobs?) for AutomationSchedules: see models.py
    - Error Handling:
      * Implement timeout mechanism for commands
      * Add retry logic for failed commands
      * Update device logs based on status messages from ESP32
  
2. Forgot password
3. WebSockets for live data
4. Sqlite --> PostGres
5. Set MQTT QoS for sensor and control messages - 0 and 1 respectively?


Other (run commands):
mosquitto_sub -h "broker.emqx.io" -t "futurefish/ponds/#" -u "futurefish_backend" -P "7-33@98:epY}" -v 
uvicorn FutureFish.asgi:application --reload
