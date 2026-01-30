-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ENUMS
CREATE TYPE user_role AS ENUM ('PARENT', 'DRIVER', 'ADMIN');
CREATE TYPE attendance_status AS ENUM ('BOARDED', 'DROPPED_OFF');

-- 1. Core Entities

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role user_role NOT NULL,
    name TEXT NOT NULL,
    auth_token TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Buses Table
CREATE TABLE buses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_number TEXT NOT NULL,
    camera_stream_url TEXT,
    iot_device_id TEXT UNIQUE NOT NULL, -- Hardware ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Students Table
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    nfc_tag_id TEXT UNIQUE NOT NULL,
    home_location GEOGRAPHY(POINT, 4326),
    name TEXT NOT NULL, -- Added name for clarity, though not explicitly in minimalistic spec, usually needed.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Operational Data

-- Routes Table
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bus_id UUID REFERENCES buses(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stops Table
CREATE TABLE stops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id UUID REFERENCES routes(id) ON DELETE CASCADE,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    sequence_order INTEGER NOT NULL,
    assigned_student_id UUID REFERENCES students(id) ON DELETE SET NULL, -- Nullable if a stop serves multiple or is generic, but spec assumes link.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Live Data

-- Trip Logs (High volume data)
CREATE TABLE trip_logs (
    id BIGSERIAL PRIMARY KEY,
    bus_id UUID REFERENCES buses(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    speed FLOAT,
    battery_level FLOAT -- Added based on payload example in prompt
);

-- Attendance Events
CREATE TABLE attendance_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    bus_id UUID REFERENCES buses(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status attendance_status NOT NULL,
    location GEOGRAPHY(POINT, 4326) -- Where the scan happened
);

-- Indexes for Performance
CREATE INDEX idx_users_auth_token ON users(auth_token);
CREATE INDEX idx_buses_iot_device_id ON buses(iot_device_id);
CREATE INDEX idx_students_nfc_tag_id ON students(nfc_tag_id);
CREATE INDEX idx_trip_logs_bus_id_timestamp ON trip_logs(bus_id, timestamp DESC);
CREATE INDEX idx_trip_logs_location ON trip_logs USING GIST(location); -- Spatial Index
CREATE INDEX idx_attendance_events_student_id ON attendance_events(student_id);
CREATE INDEX idx_attendance_events_bus_id ON attendance_events(bus_id);

