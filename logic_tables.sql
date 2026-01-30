-- Tracks who is currently on which bus
CREATE TABLE IF NOT EXISTS bus_manifest (
    bus_id VARCHAR(50),
    student_id VARCHAR(50),
    boarded_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (bus_id, student_id)
);

-- Tracks the stops (Drop-off points)
CREATE TABLE IF NOT EXISTS route_stops (
    stop_id SERIAL PRIMARY KEY,
    stop_name VARCHAR(100),
    location GEOGRAPHY(POINT, 4326),
    assigned_student_id VARCHAR(50)
);
