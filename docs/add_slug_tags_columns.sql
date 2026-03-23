-- Add slug and tags columns to videos table
ALTER TABLE videos ADD COLUMN IF NOT EXISTS slug text;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS tags jsonb DEFAULT NULL;

-- Create unique index on slug
CREATE UNIQUE INDEX IF NOT EXISTS videos_slug_idx ON videos (slug);

-- Backfill existing videos with slugs from titles
UPDATE videos SET slug =
  regexp_replace(
    regexp_replace(
      regexp_replace(lower(title), '[^a-z0-9\s-]', '', 'g'),
      '\s+', '-', 'g'
    ),
    '-+', '-', 'g'
  )
WHERE slug IS NULL;
