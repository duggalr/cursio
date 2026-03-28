-- Add source_url to track where content came from (blog post URL, paper link, etc.)
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS source_url text DEFAULT NULL;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS source_url text DEFAULT NULL;
