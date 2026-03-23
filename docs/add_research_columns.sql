-- Add web search / research support columns
-- Run this in Supabase SQL Editor

-- Add use_research flag to generation_jobs
ALTER TABLE generation_jobs
ADD COLUMN IF NOT EXISTS use_research boolean DEFAULT false;

-- Add sources (JSON array of {title, url}) to videos
ALTER TABLE videos
ADD COLUMN IF NOT EXISTS sources jsonb DEFAULT NULL;
