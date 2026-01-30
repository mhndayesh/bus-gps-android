import mqtt from 'mqtt';
import dotenv from 'dotenv';
import { connectRedis } from './db/redis';
import { handleTelemetry } from './handlers/telemetry';

dotenv.config();

const MQTT_BROKER = process.env.MQTT_BROKER_URL || 'mqtt://localhost:1883';
const TELEMETRY_TOPIC_PATTERN = /^bus\/([a-f0-9\-]+)\/telemetry$/; // Regex to capture bus_id

const client = mqtt.connect(MQTT_BROKER);

const startService = async () => {
    // Connect to Redis first
    await connectRedis();
    console.log('Connected to Redis');

    // MQTT Events
    client.on('connect', () => {
        console.log(`Connected to MQTT Broker at ${MQTT_BROKER}`);

        // Subscribe to all bus telemetry using wildcard
        client.subscribe('bus/+/telemetry', (err) => {
            if (!err) {
                console.log('Subscribed to "bus/+/telemetry"');
            } else {
                console.error('Subscription error:', err);
            }
        });
    });

    client.on('message', async (topic, message) => {
        // message is Buffer
        const payloadStr = message.toString();
        console.log(`Received message on ${topic}`);

        // Extract bus_id from topic
        const match = topic.match(TELEMETRY_TOPIC_PATTERN);
        if (match && match[1]) {
            const busId = match[1];
            try {
                const payload = JSON.parse(payloadStr);
                // Call Handler
                await handleTelemetry(busId, payload);
            } catch (e) {
                console.error('Failed to parse JSON payload:', e);
            }
        }
    });
};

startService().catch(err => {
    console.error('Failed to start service:', err);
    process.exit(1);
});
