-- Add paper-related columns to generation_jobs
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS paper_text text DEFAULT NULL;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS paper_title text DEFAULT NULL;
