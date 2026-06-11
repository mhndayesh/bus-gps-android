#!/bin/bash

# 1. Start the background listener (MQTT + DB) under a supervisor loop so a crash
#    (broker outage, DB blip at boot) is logged and auto-restarted instead of
#    silently dying while the container still looks healthy.
echo "Starting Listener (supervised)..."
(
  while true; do
    python listener.py
    echo "⚠️  listener.py exited (code $?). Restarting in 5s..."
    sleep 5
  done
) &

# 2. Start the Web App (Gunicorn). Stays in foreground to keep the container alive.
#    DB migrations run inside web_app.py so gunicorn passes Railway health checks fast.
echo "Starting Web App..."
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_app:app
