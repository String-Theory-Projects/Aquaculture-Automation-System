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
