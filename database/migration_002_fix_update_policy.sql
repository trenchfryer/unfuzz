-- Migration 002: Fix UPDATE RLS policy for images table
-- Allow users to update images in their own teams, not just projects

-- Drop the old restrictive policy
DROP POLICY IF EXISTS "Users can update images in own projects" ON images;

-- Create new policy that allows updates for both project-based AND team-based images
CREATE POLICY "Users can update images in own projects or teams"
ON images
FOR UPDATE
TO public
USING (
  -- Allow if image is in user's project
  (project_id IN (
    SELECT id FROM projects WHERE user_id = auth.uid()
  ))
  OR
  -- Allow if image is in user's team
  (team_id IN (
    SELECT id FROM teams WHERE user_id = auth.uid()
  ))
  OR
  -- Allow if image has no project_id but user owns the team
  (project_id IS NULL AND team_id IN (
    SELECT id FROM teams WHERE user_id = auth.uid()
  ))
);
