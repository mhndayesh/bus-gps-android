-- Add student_code column to students table
ALTER TABLE students ADD COLUMN IF NOT EXISTS student_code VARCHAR(50);
-- Make it unique to ensure no two students have the same code
ALTER TABLE students ADD CONSTRAINT students_student_code_key UNIQUE (student_code);
