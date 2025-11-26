-- Migration 002: Add home and away jersey support
-- Adds separate logo and color fields for home and away jerseys

-- Add new columns for home jersey (rename existing to home)
ALTER TABLE teams
  ADD COLUMN IF NOT EXISTS home_logo_url TEXT,
  ADD COLUMN IF NOT EXISTS home_logo_storage_path TEXT,
  ADD COLUMN IF NOT EXISTS home_primary_color VARCHAR(7),
  ADD COLUMN IF NOT EXISTS home_secondary_color VARCHAR(7),
  ADD COLUMN IF NOT EXISTS home_tertiary_color VARCHAR(7);

-- Add new columns for away jersey
ALTER TABLE teams
  ADD COLUMN IF NOT EXISTS away_logo_url TEXT,
  ADD COLUMN IF NOT EXISTS away_logo_storage_path TEXT,
  ADD COLUMN IF NOT EXISTS away_primary_color VARCHAR(7),
  ADD COLUMN IF NOT EXISTS away_secondary_color VARCHAR(7),
  ADD COLUMN IF NOT EXISTS away_tertiary_color VARCHAR(7);

-- Migrate existing data: copy old logo/colors to home jersey
UPDATE teams
SET
  home_logo_url = logo_url,
  home_logo_storage_path = logo_storage_path,
  home_primary_color = primary_color,
  home_secondary_color = secondary_color
WHERE home_logo_url IS NULL;

-- Keep old columns for backward compatibility (will deprecate later)
COMMENT ON COLUMN teams.logo_url IS 'DEPRECATED: Use home_logo_url instead';
COMMENT ON COLUMN teams.logo_storage_path IS 'DEPRECATED: Use home_logo_storage_path instead';
COMMENT ON COLUMN teams.primary_color IS 'DEPRECATED: Use home_primary_color instead';
COMMENT ON COLUMN teams.secondary_color IS 'DEPRECATED: Use home_secondary_color instead';

-- Add comments to new columns
COMMENT ON COLUMN teams.home_logo_url IS 'URL to home jersey logo image';
COMMENT ON COLUMN teams.away_logo_url IS 'URL to away jersey logo image';
COMMENT ON COLUMN teams.home_primary_color IS 'Primary color (hex) for home jersey';
COMMENT ON COLUMN teams.home_secondary_color IS 'Secondary color (hex) for home jersey';
COMMENT ON COLUMN teams.home_tertiary_color IS 'Tertiary color (hex) for home jersey';
COMMENT ON COLUMN teams.away_primary_color IS 'Primary color (hex) for away jersey';
COMMENT ON COLUMN teams.away_secondary_color IS 'Secondary color (hex) for away jersey';
COMMENT ON COLUMN teams.away_tertiary_color IS 'Tertiary color (hex) for away jersey';
