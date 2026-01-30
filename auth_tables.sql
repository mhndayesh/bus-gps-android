-- 1. Add Password Column (assuming plaintext for prototype, but would be hashed in production)
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. Set Default Passwords (simple for testing)
-- Super Admin
UPDATE users SET password_hash = 'admin123' WHERE role = 'SUPER_ADMIN';

-- School Admin (If any exist)
UPDATE users SET password_hash = 'school123' WHERE role = 'SCHOOL_ADMIN';

-- Parent (If any exist)
UPDATE users SET password_hash = 'parent123' WHERE role = 'PARENT';
