import paho.mqtt.client as mqtt
import json
import time

broker = "localhost"
topic_base = "bus/e5605218-5605-4b6b-ab3a-292e112db82e" 
bus_uuid = "e5605218-5605-4b6b-ab3a-292e112db82e"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(broker, 1883)

def publish(type, data):
    topic = f"{topic_base}/{type}"
    print(f"Sending {type} -> {data}")
    client.publish(topic, json.dumps(data))
    time.sleep(1)

# 1. Student Boards
publish("nfc", {"nfc_id": "STUDENT_01", "event": "BOARDING"})

# 2. Bus Drives (Far away)
publish("telemetry", {"lat": 24.0000, "lng": 46.0000, "speed": 60})

# 3. Bus Arrives at Stop 'Home A' (24.7136, 46.6753)
# logic should trigger ALERT because STUDENT_01 is still on board
publish("telemetry", {"lat": 24.7136, "lng": 46.6753, "speed": 5})

print("Test Sequence Complete. Check Listener Output for ALERT.")
client.disconnect()
