# Stage 1: Base build stage
FROM python:3.13-slim AS builder
 
# Create the app directory
RUN mkdir /app
 
# Set the working directory
WORKDIR /app
 
# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
 
# Install dependencies first for caching benefit
RUN pip install --upgrade pip 
COPY requirements.txt /app/ 
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy project files
COPY . .

# Set the entrypoint
ENTRYPOINT ["./entrypoint.prod.sh"]

# # Copy project files
# COPY . /app/

# # Collect static files
# RUN python manage.py collectstatic --noinput

# # Run gunicorn
# CMD ["gunicorn", "FutureFish.wsgi", "--bind", "0.0.0.0:8000"]
