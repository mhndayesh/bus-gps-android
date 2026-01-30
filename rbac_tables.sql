-- 1. Create Schools (The Containers)
CREATE TABLE IF NOT EXISTS schools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(255)
);

-- 2. Update Users to belong to a School
-- Adding columns if they don't exist (using DO block for safety if re-run, or just simple ALTER)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) CHECK (role IN ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PARENT', 'DRIVER')),
ADD COLUMN IF NOT EXISTS school_id INT REFERENCES schools(id); 

-- 3. Update Students to belong to a School (Critical for filtering)
ALTER TABLE students
ADD COLUMN IF NOT EXISTS school_id INT REFERENCES schools(id);

-- 4. Initial Seed (Create the Super Admin)
INSERT INTO schools (name) VALUES ('Global HQ') ON CONFLICT DO NOTHING;
-- Note: User insertion might fail if name is not unique constraint, but we'll try. 
-- Assuming we want to ensure at least one admin exists.
INSERT INTO users (name, role, school_id) VALUES ('The Boss', 'SUPER_ADMIN', 1);
