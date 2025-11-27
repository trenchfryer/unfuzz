# UnFuzz Database Setup

This directory contains the database schema and migrations for the UnFuzz application.

## Overview

UnFuzz uses **Supabase** (PostgreSQL) as its database backend, providing:
- User authentication with Google SSO
- Multi-tenant data isolation with Row Level Security (RLS)
- Team and player management
- Image storage and AI analysis results
- Project/session management
- Export and job queue functionality

## Database Schema

### Core Tables

1. **users** - User accounts and subscription information
2. **projects** - Photo culling projects/sessions
3. **images** - Individual images with AI analysis results and EXIF metadata
4. **teams** - Sports teams for player recognition
5. **players** - Team rosters with jersey numbers for AI matching
6. **team_members** - Team collaborators and access control
7. **duplicate_groups** - Groups of duplicate or similar images
8. **exports** - Export job history
9. **analysis_jobs** - Background job queue for AI analysis

### Key Features

- **Team Player Recognition**: AI can identify players by jersey number and match them to team rosters
- **Multi-user Collaboration**: Teams can have multiple members with different permission levels
- **Row Level Security**: Automatic data isolation between users and teams
- **Auto-matching**: Jersey numbers detected by AI are automatically matched to players
- **Comprehensive Metadata**: EXIF data, camera settings, AI scores, and recommendations

## Setup Instructions

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your project URL and anon key
3. Update your `.env` file with the credentials:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   SUPABASE_SERVICE_KEY=your-service-key-here
   ```

### 2. Run Database Migrations

Execute these SQL files in your Supabase SQL Editor in order:

1. **schema.sql** - Creates the base schema (users, projects, images, etc.)
   ```sql
   -- Copy and paste the contents of schema.sql into Supabase SQL Editor
   ```

2. **migration_001_team_player_support.sql** - Adds team/player recognition support
   ```sql
   -- Copy and paste the contents of migration_001_team_player_support.sql
   ```

3. **migration_002_fix_update_policy.sql** - Fixes RLS UPDATE policy for team-based images
   ```sql
   -- Copy and paste the contents of migration_002_fix_update_policy.sql
   ```
   **Important**: This migration fixes player override edits not persisting. Required for team mode functionality.

### 3. Enable Google OAuth

1. In your Supabase dashboard, go to Authentication → Providers
2. Enable Google provider
3. Add your Google OAuth credentials
4. Add authorized redirect URLs:
   - `http://localhost:3005/auth/callback` (development)
   - `https://your-domain.com/auth/callback` (production)

### 4. Configure Storage Buckets

Create the following storage buckets in Supabase:

1. **images** - For uploaded photos
   - Public: No
   - File size limit: 50MB
   - Allowed MIME types: image/jpeg, image/png, image/heic

2. **team-logos** - For team logo uploads
   - Public: Yes (for display purposes)
   - File size limit: 5MB
   - Allowed MIME types: image/jpeg, image/png, image/svg+xml

3. **thumbnails** - For image thumbnails
   - Public: Yes
   - File size limit: 2MB
   - Allowed MIME types: image/jpeg, image/png

## Database Relationships

```
users
  └─→ teams (owner)
  └─→ projects
  └─→ team_members (collaborators)

teams
  └─→ players (roster)
  └─→ projects (team projects)
  └─→ images (team images)
  └─→ team_members (access control)

projects
  └─→ images
  └─→ duplicate_groups
  └─→ exports

images
  ├─→ team (optional)
  ├─→ player (auto-matched by jersey number)
  └─→ project
```

## Security

### Row Level Security (RLS)

All tables have RLS enabled with policies that:
- Users can only see their own data
- Team members can see team data based on permissions
- Images are visible to project owners and team members
- Automatic data isolation between tenants

### Permission Levels

**Team Member Roles:**
- **owner** - Full control over team, can delete team
- **admin** - Can manage members and roster
- **editor** - Can edit roster and manage images
- **viewer** - Read-only access to team images

**Team Permissions:**
- `can_view` - Can see team images and roster
- `can_edit` - Can edit images and metadata
- `can_manage_roster` - Can add/edit/delete players
- `can_manage_members` - Can invite/remove team members

## Team Player Recognition

### How it Works

1. User creates a team and uploads team logo
2. User adds players with names and jersey numbers
3. When uploading images with "Team Mode" enabled:
   - AI analyzes the image and detects jersey numbers
   - AI compares team logo in image to stored logo
   - Detected jersey number is automatically matched to player
   - Player name is added to image metadata
4. Users can filter and sort images by player name

### AI Prompt Enhancement

The AI analysis prompt includes:
- Team logo image for visual matching
- List of player names and jersey numbers
- Request to detect and identify jersey numbers
- Request to confirm team logo match

## Future Enhancements

- [ ] Stripe subscription integration
- [ ] Advanced analytics (per-player statistics)
- [ ] Batch player import from CSV
- [ ] Team season archives
- [ ] Public team galleries (with permission)
- [ ] Email invitations for team members
- [ ] Real-time collaboration features

## Troubleshooting

### Connection Issues

If you can't connect to Supabase:
1. Verify your credentials in `.env`
2. Check that your IP is not blocked
3. Ensure RLS policies are correct
4. Check Supabase dashboard for any errors

### Migration Errors

If migration fails:
1. Check for existing tables that might conflict
2. Ensure UUID extension is enabled
3. Run migrations in order (schema.sql first)
4. Check Supabase logs for detailed errors

### RLS Policy Issues

If users can't access their data:
1. Verify user is authenticated (`auth.uid()` returns user ID)
2. Check RLS policies are enabled on all tables
3. Test policies in Supabase SQL Editor
4. Ensure user_id matches authenticated user

### Player Override Edits Not Persisting

**Symptoms**: Player name or jersey number edits appear to save (no error) but revert after page refresh.

**Cause**: RLS UPDATE policy blocking modifications on team-based images.

**Solution**: Run migration_002_fix_update_policy.sql to update the RLS policy.

**Verification**:
```sql
-- Check if images have team_id set
SELECT id, filename, team_id, project_id FROM images LIMIT 10;

-- Verify UPDATE policy exists
SELECT policyname FROM pg_policies
WHERE tablename = 'images' AND cmd = 'UPDATE';
```

**Expected**: Policy should be named "Users can update images in own projects or teams"

## Development Tips

### Testing Locally

You can test the schema locally using:
```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase
supabase start

# Apply migrations
supabase db push
```

### Sample Data

To add sample data for testing:
```sql
-- Insert test user
INSERT INTO users (id, email, subscription_tier)
VALUES ('your-auth-user-id', 'test@example.com', 'pro');

-- Insert test team
INSERT INTO teams (user_id, name, sport)
VALUES ('your-auth-user-id', 'Test Warriors', 'basketball');

-- Insert test players
INSERT INTO players (team_id, jersey_number, first_name, last_name, position)
VALUES
  ('team-id', '23', 'John', 'Doe', 'Guard'),
  ('team-id', '10', 'Jane', 'Smith', 'Forward');
```

## Support

For issues or questions:
- Check the [Supabase documentation](https://supabase.com/docs)
- Review RLS policies in the dashboard
- Check application logs for detailed errors
