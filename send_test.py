import paho.mqtt.client as mqtt
import json

broker = "localhost"
port = 1883
topic = "bus/e5605218-5605-4b6b-ab3a-292e112db82e/telemetry"
payload = {
    "bus_id": "e5605218-5605-4b6b-ab3a-292e112db82e", 
    "lat": 24.7136, 
    "lng": 46.6753, 
    "speed": 45
}

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    client.connect(broker, port)
    client.publish(topic, json.dumps(payload))
    print(f"Published to {topic}: {payload}")
    client.disconnect()
except Exception as e:
    print(f"Failed to publish: {e}")
