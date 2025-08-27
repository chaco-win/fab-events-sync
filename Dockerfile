FROM python:3.11-slim

# minimal deps + timezone support + tiny cron runner
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tzdata curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# supercronic = simple cron runner for containers
RUN curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
     -o /usr/local/bin/supercronic && chmod +x /usr/local/bin/supercronic

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory
RUN mkdir -p /app/logs

# app files
COPY fab_local_dfw_events.py .
COPY fab_major_global_events.py .
COPY clean_calendar.py .
COPY crontab /etc/crontab
COPY config.toml ./config.toml

ENV PYTHONUNBUFFERED=1

# run cron (calls python scripts per crontab)
CMD ["/usr/local/bin/supercronic","-passthrough-logs","/etc/crontab"]
