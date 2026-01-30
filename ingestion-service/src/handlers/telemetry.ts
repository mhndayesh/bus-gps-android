import { query } from '../db/postgres';
import redisClient from '../db/redis';

interface TelemetryPayload {
    lat: number;
    lng: number;
    speed: number;
    battery?: number; // Optional in case needed
}

export const handleTelemetry = async (busId: string, payload: TelemetryPayload) => {
    const { lat, lng, speed, battery } = payload;

    try {
        // 1. Write to PostgreSQL (trip_logs)
        // Note: ST_MakePoint takes (longitude, latitude)
        const insertQuery = `
      INSERT INTO trip_logs (bus_id, location, speed, battery_level)
      VALUES ($1, ST_SetSRID(ST_MakePoint($2, $3), 4326), $4, $5)
    `;

        // We execute async but we don't necessarily have to wait for this to return to acknowledge (QoS 0 usually)
        // But for safety we await.
        await query(insertQuery, [busId, lng, lat, speed, battery || null]);
        console.log(`[PG] Saved log for bus ${busId}: ${lat}, ${lng}`);

        // 2. Update Redis Cache (Real-time)
        // storing complex object as JSON string or Hash. JSON string is simpler for now.
        const redisKey = `bus:${busId}:location`;
        const redisData = JSON.stringify({
            bus_id: busId,
            lat,
            lng,
            speed,
            timestamp: new Date().toISOString(),
            battery
        });

        await redisClient.set(redisKey, redisData);
        // Optionally expire after some time inside logic, but buses should ping constantly.
        console.log(`[Redis] Updated cache for bus ${busId}`);

    } catch (err) {
        console.error(`Error processing telemetry for bus ${busId}:`, err);
    }
};
