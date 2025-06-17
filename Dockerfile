FROM python:3.11.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UV_INSTALL_DIR="/usr/local/bin"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    unzip \
    patch && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade setuptools

RUN pip install --upgrade setuptools

ADD --chmod=655 https://astral.sh/uv/0.2.34/install.sh /install.sh
RUN /install.sh && rm /install.sh

COPY requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip /root/.cargo/bin/uv pip install --system --no-cache -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application with Uvicorn (ASGI)
CMD ["uvicorn", "FutureFish.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
