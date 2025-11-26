-- Migration 002: Fix player jersey_number constraints for soft deletes
-- This allows inactive players to have NULL jersey_number so numbers can be reused

-- Step 1: Drop the existing unique constraint
ALTER TABLE players DROP CONSTRAINT IF EXISTS players_team_id_jersey_number_key;

-- Step 2: Make jersey_number nullable (allow NULL)
ALTER TABLE players ALTER COLUMN jersey_number DROP NOT NULL;

-- Step 3: Create a partial unique index that only applies to active players
-- This allows: multiple inactive players with NULL jersey_number, but unique numbers for active players
CREATE UNIQUE INDEX players_active_jersey_unique
ON players (team_id, jersey_number)
WHERE is_active = true;

-- Step 4: Clean up existing inactive players - set their jersey_number to NULL
UPDATE players
SET jersey_number = NULL
WHERE is_active = false AND jersey_number IS NOT NULL;

-- Verify the changes
SELECT
    'Migration 002 completed' as status,
    COUNT(*) FILTER (WHERE is_active = false AND jersey_number IS NULL) as inactive_players_cleared,
    COUNT(*) FILTER (WHERE is_active = true) as active_players
FROM players;
