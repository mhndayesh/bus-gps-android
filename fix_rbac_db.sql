-- 1. Fix Enum Types (Add missing roles)
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SUPER_ADMIN';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SCHOOL_ADMIN';

-- 2. Insert The Boss (Super Admin) if not exists
INSERT INTO users (name, role, school_id) 
VALUES ('The Boss', 'SUPER_ADMIN', 1)
ON CONFLICT DO NOTHING;

-- 3. Create a Test Parent with a KNOWN UUID for easy testing
-- We force the UUID so you can type it easily: '00000000-0000-0000-0000-000000000001'
INSERT INTO users (id, name, role, school_id) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Parent', 'PARENT', 1)
ON CONFLICT (id) DO NOTHING;
