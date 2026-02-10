#!/bin/bash

# 0. Initialize Database
echo "Running Migrations..."
python create_tables.py

# 1. Start the Background Listener (Handling MQTT & DB)
# We use '&' to run it in background so script continues
echo "Starting Listener..."
python listener.py &

# 2. Start the Web App (Gunicorn Production Server)
# This stays in foreground to keep container alive
echo "Starting Web App..."
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_app:app
