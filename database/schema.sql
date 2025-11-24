-- UnFuzz Database Schema for Supabase (PostgreSQL)
-- Run this SQL in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  subscription_tier VARCHAR(50) DEFAULT 'free',
  total_images_processed INTEGER DEFAULT 0,
  monthly_images_used INTEGER DEFAULT 0,
  last_reset_date DATE DEFAULT CURRENT_DATE
);

-- Projects/Sessions table
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  status VARCHAR(50) DEFAULT 'processing', -- processing, completed, failed, archived
  total_images INTEGER DEFAULT 0,
  processed_images INTEGER DEFAULT 0,
  selected_images INTEGER DEFAULT 0,
  settings JSONB DEFAULT '{}'::jsonb
);

-- Images table
CREATE TABLE IF NOT EXISTS images (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  filename VARCHAR(500) NOT NULL,
  original_url TEXT NOT NULL,
  thumbnail_url TEXT,
  file_size BIGINT,
  width INTEGER,
  height INTEGER,
  format VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- EXIF data
  exif_data JSONB,
  camera_make VARCHAR(100),
  camera_model VARCHAR(100),
  lens_model VARCHAR(100),
  focal_length NUMERIC,
  aperture NUMERIC,
  shutter_speed VARCHAR(50),
  iso INTEGER,
  capture_time TIMESTAMP,

  -- Analysis results
  analysis_status VARCHAR(50) DEFAULT 'pending', -- pending, analyzing, completed, failed
  analysis_completed_at TIMESTAMP,
  overall_score NUMERIC(5,2),

  -- Individual factor scores (0-100)
  scores JSONB, -- Stores all 30+ factor scores as JSON object

  -- AI insights
  ai_summary TEXT,
  detected_issues TEXT[],
  recommendations TEXT[],
  critical_defects TEXT[],

  -- Categorization
  quality_tier VARCHAR(20), -- excellent, good, acceptable, poor, reject
  is_duplicate BOOLEAN DEFAULT FALSE,
  duplicate_group_id UUID,

  -- User actions
  user_selected BOOLEAN DEFAULT NULL,
  user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
  user_notes TEXT,
  is_favorite BOOLEAN DEFAULT FALSE,

  -- Perceptual hash for duplicate detection
  phash VARCHAR(64),
  dhash VARCHAR(64),

  -- Subject analysis
  faces_detected INTEGER DEFAULT 0,
  eyes_status VARCHAR(50), -- all_open, some_closed, blink_detected, no_faces
  has_people BOOLEAN DEFAULT FALSE
);

-- Duplicate groups table
CREATE TABLE IF NOT EXISTS duplicate_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  representative_image_id UUID REFERENCES images(id) ON DELETE SET NULL,
  image_count INTEGER DEFAULT 0,
  group_type VARCHAR(50), -- exact_duplicate, near_duplicate, burst_sequence
  similarity_score NUMERIC(5,2),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Export history
CREATE TABLE IF NOT EXISTS exports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  destination VARCHAR(100), -- 'local', 'google_drive', 's3', etc.
  image_count INTEGER,
  export_settings JSONB,
  status VARCHAR(50), -- pending, in_progress, completed, failed
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  download_url TEXT,
  error_message TEXT
);

-- Analysis jobs queue (for background processing)
CREATE TABLE IF NOT EXISTS analysis_jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  image_id UUID REFERENCES images(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
  created_at TIMESTAMP DEFAULT NOW(),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  priority INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_project ON images(project_id);
CREATE INDEX IF NOT EXISTS idx_images_score ON images(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_images_quality_tier ON images(quality_tier);
CREATE INDEX IF NOT EXISTS idx_images_phash ON images(phash);
CREATE INDEX IF NOT EXISTS idx_images_dhash ON images(dhash);
CREATE INDEX IF NOT EXISTS idx_images_analysis_status ON images(analysis_status);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_project ON duplicate_groups(project_id);
CREATE INDEX IF NOT EXISTS idx_exports_project ON exports(project_id);
CREATE INDEX IF NOT EXISTS idx_exports_user ON exports(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_images_capture_time ON images(capture_time);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_images_updated_at BEFORE UPDATE ON images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update project statistics
CREATE OR REPLACE FUNCTION update_project_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects
    SET
        total_images = (SELECT COUNT(*) FROM images WHERE project_id = NEW.project_id),
        processed_images = (SELECT COUNT(*) FROM images WHERE project_id = NEW.project_id AND analysis_status = 'completed'),
        selected_images = (SELECT COUNT(*) FROM images WHERE project_id = NEW.project_id AND user_selected = TRUE)
    WHERE id = NEW.project_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to update project stats when images change
CREATE TRIGGER update_project_stats_trigger
AFTER INSERT OR UPDATE OR DELETE ON images
    FOR EACH ROW EXECUTE FUNCTION update_project_stats();

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- Projects policies
CREATE POLICY "Users can view own projects"
    ON projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create projects"
    ON projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects"
    ON projects FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects"
    ON projects FOR DELETE
    USING (auth.uid() = user_id);

-- Images policies
CREATE POLICY "Users can view images in own projects"
    ON images FOR SELECT
    USING (project_id IN (SELECT id FROM projects WHERE user_id = auth.uid()));

CREATE POLICY "Users can insert images in own projects"
    ON images FOR INSERT
    WITH CHECK (project_id IN (SELECT id FROM projects WHERE user_id = auth.uid()));

CREATE POLICY "Users can update images in own projects"
    ON images FOR UPDATE
    USING (project_id IN (SELECT id FROM projects WHERE user_id = auth.uid()));

CREATE POLICY "Users can delete images in own projects"
    ON images FOR DELETE
    USING (project_id IN (SELECT id FROM projects WHERE user_id = auth.uid()));

-- Sample data for testing (optional - remove in production)
-- INSERT INTO users (email, subscription_tier) VALUES
-- ('test@unfuzz.com', 'pro');

COMMENT ON TABLE users IS 'User accounts and subscription information';
COMMENT ON TABLE projects IS 'Photo culling projects/sessions';
COMMENT ON TABLE images IS 'Individual images with analysis results';
COMMENT ON TABLE duplicate_groups IS 'Groups of duplicate or similar images';
COMMENT ON TABLE exports IS 'Export job history';
COMMENT ON TABLE analysis_jobs IS 'Background job queue for AI analysis';
