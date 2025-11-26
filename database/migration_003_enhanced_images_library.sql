-- Migration 003: Enhanced Images Library
-- Creates table for saved/enhanced images with player associations and download tracking

CREATE TABLE IF NOT EXISTS enhanced_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    original_image_id UUID REFERENCES images(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    player_id UUID REFERENCES players(id) ON DELETE SET NULL,

    -- Image storage
    enhanced_url TEXT NOT NULL,
    enhanced_storage_path TEXT NOT NULL,
    thumbnail_url TEXT,

    -- Enhancement details
    enhancement_settings JSONB,  -- Store the enhancement parameters used
    applied_adjustments JSONB,   -- Actual adjustments applied

    -- Player override (allow manual correction)
    player_name_override TEXT,  -- If AI got it wrong, manually corrected name
    jersey_number_override TEXT,

    -- Metadata
    title TEXT,
    description TEXT,
    tags TEXT[],  -- Array of tags for searching/filtering

    -- Stats
    download_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for fast filtering
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enhanced_images_user ON enhanced_images(user_id);
CREATE INDEX IF NOT EXISTS idx_enhanced_images_team ON enhanced_images(team_id);
CREATE INDEX IF NOT EXISTS idx_enhanced_images_player ON enhanced_images(player_id);
CREATE INDEX IF NOT EXISTS idx_enhanced_images_created ON enhanced_images(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enhanced_images_tags ON enhanced_images USING GIN(tags);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_enhanced_images_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_enhanced_images_updated_at ON enhanced_images;
CREATE TRIGGER trigger_enhanced_images_updated_at
    BEFORE UPDATE ON enhanced_images
    FOR EACH ROW
    EXECUTE FUNCTION update_enhanced_images_updated_at();

-- Add column to images table to track if image has been enhanced and saved
ALTER TABLE images
    ADD COLUMN IF NOT EXISTS is_saved_to_library BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS player_name_override TEXT,  -- Manual player name correction
    ADD COLUMN IF NOT EXISTS jersey_number_override TEXT;  -- Manual jersey number correction

-- Comments
COMMENT ON TABLE enhanced_images IS 'Library of enhanced/saved images with player associations';
COMMENT ON COLUMN enhanced_images.player_name_override IS 'Manually corrected player name if AI detection was wrong';
COMMENT ON COLUMN enhanced_images.jersey_number_override IS 'Manually corrected jersey number if AI detection was wrong';
COMMENT ON COLUMN images.player_name_override IS 'Temporary override before saving to library';
COMMENT ON COLUMN images.jersey_number_override IS 'Temporary override before saving to library';
