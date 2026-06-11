#!/bin/bash
# Usage: ./logcat.sh
# Streams crash logs + app logs from the connected device/emulator in real time.
# Shows only BusGPS app output + any fatal crashes.

export PATH=$PATH:/home/mhnd/Android/Sdk/platform-tools

echo "=== Clearing old logs ==="
adb logcat -c

echo "=== Streaming logs (Ctrl+C to stop) ==="
adb logcat AndroidRuntime:E com.busgps.android:D OkHttp:D *:S
