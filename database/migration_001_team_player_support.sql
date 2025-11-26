-- Migration 001: Add Team Player Recognition Support
-- This migration adds tables for teams, players, and team member access

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL, -- Team owner (references auth.users)
  name VARCHAR(255) NOT NULL,
  sport VARCHAR(100), -- basketball, soccer, football, etc.
  season VARCHAR(100), -- e.g., "2024-2025", "Spring 2024"
  logo_url TEXT, -- Stored in Supabase Storage
  logo_storage_path TEXT, -- Storage bucket path
  primary_color VARCHAR(7), -- Hex color code
  secondary_color VARCHAR(7), -- Hex color code
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
  jersey_number VARCHAR(10) NOT NULL, -- Can be "12", "3A", etc.
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  position VARCHAR(50), -- Guard, Forward, Midfielder, etc.
  grade_year VARCHAR(20), -- Freshman, Sophomore, 9th, 10th, etc.
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(team_id, jersey_number) -- Each team has unique jersey numbers
);

-- Team members/collaborators table (for sharing access)
CREATE TABLE IF NOT EXISTS team_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
  user_id UUID NOT NULL, -- References auth.users
  role VARCHAR(50) DEFAULT 'viewer', -- owner, admin, editor, viewer
  can_view BOOLEAN DEFAULT TRUE,
  can_edit BOOLEAN DEFAULT FALSE,
  can_manage_roster BOOLEAN DEFAULT FALSE,
  can_manage_members BOOLEAN DEFAULT FALSE,
  invited_by UUID, -- References auth.users
  invited_at TIMESTAMP DEFAULT NOW(),
  accepted_at TIMESTAMP,
  status VARCHAR(50) DEFAULT 'active', -- pending, active, inactive
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(team_id, user_id)
);

-- Add team and player columns to images table
ALTER TABLE images ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE SET NULL;
ALTER TABLE images ADD COLUMN IF NOT EXISTS player_id UUID REFERENCES players(id) ON DELETE SET NULL;
ALTER TABLE images ADD COLUMN IF NOT EXISTS detected_jersey_number VARCHAR(10);
ALTER TABLE images ADD COLUMN IF NOT EXISTS player_confidence NUMERIC(3,2); -- 0.00 to 1.00
ALTER TABLE images ADD COLUMN IF NOT EXISTS team_mode_enabled BOOLEAN DEFAULT FALSE;

-- Add team reference to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES teams(id) ON DELETE SET NULL;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_teams_user ON teams(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_active ON teams(is_active);
CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_number ON players(team_id, jersey_number);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_status ON team_members(status);
CREATE INDEX IF NOT EXISTS idx_images_team ON images(team_id);
CREATE INDEX IF NOT EXISTS idx_images_player ON images(player_id);
CREATE INDEX IF NOT EXISTS idx_images_jersey_number ON images(detected_jersey_number);

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

-- Teams policies: Users can see teams they own or are members of
CREATE POLICY "Users can view own teams"
    ON teams FOR SELECT
    USING (
        user_id = auth.uid() OR
        id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active')
    );

CREATE POLICY "Users can create teams"
    ON teams FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Team owners can update teams"
    ON teams FOR UPDATE
    USING (
        user_id = auth.uid() OR
        id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_roster = TRUE)
    );

CREATE POLICY "Team owners can delete teams"
    ON teams FOR DELETE
    USING (user_id = auth.uid());

-- Players policies: Visible to team members
CREATE POLICY "Team members can view players"
    ON players FOR SELECT
    USING (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'
        )
    );

CREATE POLICY "Team editors can insert players"
    ON players FOR INSERT
    WITH CHECK (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_roster = TRUE
        )
    );

CREATE POLICY "Team editors can update players"
    ON players FOR UPDATE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_roster = TRUE
        )
    );

CREATE POLICY "Team editors can delete players"
    ON players FOR DELETE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_roster = TRUE
        )
    );

-- Team members policies
CREATE POLICY "Users can view team memberships"
    ON team_members FOR SELECT
    USING (
        user_id = auth.uid() OR
        team_id IN (SELECT id FROM teams WHERE user_id = auth.uid()) OR
        team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_members = TRUE)
    );

CREATE POLICY "Team admins can manage members"
    ON team_members FOR INSERT
    WITH CHECK (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_members = TRUE
        )
    );

CREATE POLICY "Team admins can update members"
    ON team_members FOR UPDATE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_members = TRUE
        )
    );

CREATE POLICY "Team admins can delete members"
    ON team_members FOR DELETE
    USING (
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_manage_members = TRUE
        )
    );

-- Update images policies to include team access
DROP POLICY IF EXISTS "Users can view images in own projects" ON images;
CREATE POLICY "Users can view images in own projects or team projects"
    ON images FOR SELECT
    USING (
        project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
        OR
        team_id IN (
            SELECT id FROM teams WHERE user_id = auth.uid()
            UNION
            SELECT team_id FROM team_members WHERE user_id = auth.uid() AND can_view = TRUE AND status = 'active'
        )
    );

-- Function to auto-match players based on jersey number
CREATE OR REPLACE FUNCTION match_player_to_image()
RETURNS TRIGGER AS $$
BEGIN
    -- If team_mode is enabled and jersey number detected, try to match player
    IF NEW.team_mode_enabled = TRUE AND NEW.detected_jersey_number IS NOT NULL AND NEW.team_id IS NOT NULL THEN
        -- Find matching player
        SELECT id INTO NEW.player_id
        FROM players
        WHERE team_id = NEW.team_id
        AND jersey_number = NEW.detected_jersey_number
        AND is_active = TRUE
        LIMIT 1;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Trigger to auto-match players
CREATE TRIGGER match_player_on_insert_or_update
BEFORE INSERT OR UPDATE ON images
FOR EACH ROW EXECUTE FUNCTION match_player_to_image();

-- Comments for documentation
COMMENT ON TABLE teams IS 'Sports teams for player recognition';
COMMENT ON TABLE players IS 'Team roster with jersey numbers for AI recognition';
COMMENT ON TABLE team_members IS 'Team collaborators and access control';
COMMENT ON COLUMN images.team_id IS 'Associated team for player recognition';
COMMENT ON COLUMN images.player_id IS 'Identified player in the image';
COMMENT ON COLUMN images.detected_jersey_number IS 'Jersey number detected by AI';
COMMENT ON COLUMN images.player_confidence IS 'Confidence score for player identification (0-1)';
COMMENT ON COLUMN images.team_mode_enabled IS 'Whether this image was analyzed with team mode enabled';
