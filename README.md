**Future Fish AgroTech Mobile App**
Create .env.local and define
DEBUG=True
SECRET_KEY=
SYSTEM_USERNAME=chief_fisherman
SYSTEM_EMAIL=info@futurefishagro.com
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

change dockerfile to entrypoint.local

To run docker locally:
docker run \
  -v "$(pwd)/db.sqlite3:/app/db.sqlite3" \
  -p 8000:8000 \
  --env-file .env.local \
  future-fish-dashboard




Commit Test Count: 1

_See: app.futuregishagro.com_

## Project Architecture

The Future Fish Dashboard has been restructured into a modular architecture with the following apps:

- **`core/`** - Core utilities, constants, and base models
- **`ponds/`** - Pond management, sensor data, and device controls
- **`automation/`** - Automation logic, feed events, and threshold management
- **`mqtt_client/`** - MQTT communication and device status
- **`analytics/`** - Data analysis and reporting
- **`users/`** - User management and authentication
- **`api/`** - API endpoints and documentation

## Management Commands

### Generate Dummy Sensor Data
```bash
# Generate 60 days of data for pond ID 2
python manage.py generate_dummy_sensor_data 2

# Clear existing data first
python manage.py generate_dummy_sensor_data 2 --clear

# Generate 30 days of data
python manage.py generate_dummy_sensor_data 2 --days 30
```

### Feed Statistics Management
```bash
# Rollover feed statistics (runs automatically via cron)
python manage.py rollover_feed_stats
```

## MQTT Topics

### Device-Level Topics (Currently Implemented):
- `devices/{device_id}/data/heartbeat`      # Device heartbeat (10s intervals)
- `devices/{device_id}/data/startup`       # Device startup + firmware info
- `devices/{device_id}/data/sensors`       # Sensor data from devices
- `devices/{device_id}/commands`           # Commands sent TO devices
- `devices/{device_id}/ack`                # Command acknowledgments
- `devices/{device_id}/threshold`          # Threshold updates

### MQTT Configuration:
- **Broker**: `broker.emqx.io:1883`
- **Username**: `futurefish_backend`
- **Password**: `7-33@98:epY}`
- **Client ID**: `futurefish_backend_{random_hex}`

## API Endpoints

### Feed Event Logging
- **POST** `/automation/feed/log-event/` - Log feed events from Lambda

### Pond Management
- **GET/POST** `/ponds/` - List and create ponds
- **GET/PUT/DELETE** `/ponds/{id}/` - Manage individual ponds
- **GET** `/ponds/{id}/feed-stats/` - Get feed statistics

### Automation
- **GET** `/automation/ponds/{id}/thresholds/` - Get automation thresholds
- **POST** `/automation/ponds/{id}/execute/` - Execute manual automation
- **POST** `/automation/ponds/{id}/control/feed/` - Execute feed command (DRF APIView)
- **POST** `/automation/ponds/{id}/control/water/` - Execute water control command (DRF APIView)

## To-Do:
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

## Development Commands

### MQTT Testing
```bash
# Subscribe to device data
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/data/+" -v

# Subscribe to device commands
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/commands" -v

# Subscribe to device acknowledgments
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/ack" -v
```

### Development Server
```bash
uvicorn FutureFish.asgi:application --reload
```

### Database Management
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
```

---------------------       CODESHARE       -----------------------------

name: Deploy to AWS App Runner

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

env:
  AWS_REGION: eu-west-1
  ECR_REPOSITORY: future-fish-dashboard

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    environment: production
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run migrations check
      env:
        DB_HOST: ${{ secrets.DB_HOST }}
        DB_NAME: ${{ secrets.DB_NAME }}
        DB_USER: ${{ secrets.DB_USER }}
        DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        DB_PORT: ${{ secrets.DB_PORT }}
      run: |
        python manage.py check --deploy
        python manage.py makemigrations --check --dry-run

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Build, tag, and push image to Amazon ECR
      id: build-image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        # Build Docker image with RDS support
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
          --build-arg DB_HOST=${{ secrets.DB_HOST }} \
          --build-arg DB_NAME=${{ secrets.DB_NAME }} \
          --build-arg DB_USER=${{ secrets.DB_USER }} \
          .
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

    - name: Run database migrations
      if: github.ref == 'refs/heads/main'
      env:
        DB_HOST: ${{ secrets.DB_HOST }}
        DB_NAME: ${{ secrets.DB_NAME }}
        DB_USER: ${{ secrets.DB_USER }}
        DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        DB_PORT: ${{ secrets.DB_PORT }}
      run: |
        python manage.py migrate --no-input

    - name: Collect static files
      if: github.ref == 'refs/heads/main'
      env:
        DB_HOST: ${{ secrets.DB_HOST }}
        DB_NAME: ${{ secrets.DB_NAME }}
        DB_USER: ${{ secrets.DB_USER }}
        DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        DB_PORT: ${{ secrets.DB_PORT }}
      run: |
        python manage.py collectstatic --no-input
