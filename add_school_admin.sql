-- Create a specific School Admin for testing
INSERT INTO users (name, role, school_id, password_hash) 
VALUES ('Principal Skinner', 'SCHOOL_ADMIN', 1, 'school123')
ON CONFLICT DO NOTHING;

-- Ensure Test Parent has the correct password (just in case)
UPDATE users SET password_hash = 'parent123' WHERE name = 'Test Parent';
