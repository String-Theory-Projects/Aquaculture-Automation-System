python manage.py generate_dummy_sensor_data 2  # Generate 60 days of data for pond ID 2
python manage.py generate_dummy_sensor_data 2 --clear  # Clear existing data first
python manage.py generate_dummy_sensor_data 2 --days 30  # Generate 30 days of data

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

mosquitto_sub -h "broker.emqx.io" -t "futurefish/ponds/#" -u "futurefish_backend" -P "7-33@98:epY}" -v 
uvicorn your_project.asgi:application --reload