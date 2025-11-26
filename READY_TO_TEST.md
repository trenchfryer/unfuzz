# 🎉 UnFuzz Team Management - READY TO TEST!

**Status:** Core system is COMPLETE and ready for testing!
**Date:** 2025-11-25

---

## ✅ What's Built and Running

### Backend API (Port 8015) ✅
- **Status:** Running and healthy
- **Check:** http://localhost:8015/health
- **API Docs:** http://localhost:8015/api/docs

**Endpoints:**
- `/api/v1/auth/me` - Get user profile
- `/api/v1/teams` - List/Create teams
- `/api/v1/teams/{id}` - Get/Update/Delete team
- `/api/v1/teams/{id}/logo` - Upload team logo
- `/api/v1/players/team/{id}` - List team players
- `/api/v1/players` - Create/Update/Delete players
- `/api/v1/players/bulk` - Bulk create
- `/api/v1/players/import-csv` - CSV import

### Database (Supabase) ✅
- **9 Tables Created:**
  - users, projects, images
  - teams, players, team_members
  - duplicate_groups, exports, analysis_jobs
- **RLS Enabled:** Row Level Security active
- **Auto-Matching:** Jersey number → player trigger active

### Frontend Pages ✅
**NEW PAGES CREATED:**

1. **Settings Hub** `/settings`
   - Clean navigation to all settings sections
   - Quick access to team management

2. **Teams List** `/settings/teams`
   - View all teams in card grid
   - Create new team inline
   - Edit/Delete teams
   - Shows player counts and logos

3. **Team Detail** `/settings/teams/[id]`
   - Edit team details (name, sport, season, colors)
   - Upload/delete team logo
   - Complete player roster management
   - Add/delete players with jersey numbers
   - Sortable player table

### Frontend API Client ✅
**File:** `frontend/lib/api.ts`
- Supabase auth interceptor
- All team/player methods
- Type-safe with TypeScript
- Error handling built-in

---

## 🚀 How to Test

### Step 1: Start Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8015
```

**Verify:** Visit http://localhost:8015/health
Should see: `{"status": "healthy", ...}`

### Step 2: Start Frontend
```bash
cd frontend
npm run dev
```

**Default Port:** http://localhost:3005

### Step 3: Test Team Management Flow

1. **Navigate to Settings**
   - Go to: http://localhost:3005/settings
   - You should see tabs for Teams, Profile, Billing

2. **Go to Teams Page**
   - Click "Manage Teams & Players" or navigate to `/settings/teams`
   - You should see "Create Team" button

3. **Create Your First Team**
   - Click "+ Create Team"
   - Fill in:
     - **Name:** "Warriors" (required)
     - **Sport:** "Basketball"
     - **Season:** "2024-2025"
   - Click "Create Team"
   - Team should appear in grid

4. **Manage Team Roster**
   - Click "Manage" on your team
   - You're now at `/settings/teams/{id}`
   - Upload a team logo (optional)
   - Edit team colors using color pickers

5. **Add Players**
   - Click "+ Add Player"
   - Fill in player details:
     - **Jersey #:** "23" (required)
     - **First Name:** "Michael"
     - **Last Name:** "Jordan"
     - **Position:** "Guard"
     - **Grade/Year:** "Senior"
   - Click "Add Player"
   - Player appears in roster table

6. **Add More Players**
   - Repeat to add 5-10 players with different jersey numbers
   - Players auto-sort by jersey number

7. **Edit/Delete**
   - Test deleting a player
   - Go back and edit team name/colors

---

## 🧪 API Testing (Optional)

### Test with Browser Dev Tools

Open browser console and test the API directly:

```javascript
// Import the API
import { getTeams, createTeam, createPlayer } from '/lib/api.ts';

// Get all teams
const teams = await getTeams();
console.log(teams);

// Create a team
const newTeam = await createTeam({
  name: "Lakers",
  sport: "Basketball",
  season: "2024-2025"
});
console.log(newTeam);

// Add a player
const player = await createPlayer({
  team_id: newTeam.id,
  jersey_number: "24",
  first_name: "Kobe",
  last_name: "Bryant"
});
console.log(player);
```

### Test with curl

```bash
# Get auth token from Supabase first
# Then test endpoints:

curl -H "Authorization: Bearer YOUR_TOKEN" \\
  http://localhost:8015/api/v1/teams

curl -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"Celtics","sport":"Basketball"}' \\
  http://localhost:8015/api/v1/teams
```

---

## 📊 Database Verification

### Check Data in Supabase Dashboard

1. Go to: https://supabase.com/dashboard
2. Select your project: `bstwcobrswnsaoaxhqqc`
3. Click "Table Editor"
4. Check tables:
   - **teams** - Should see your created teams
   - **players** - Should see players with jersey numbers
   - **users** - Your user record

### Query with MCP

In Claude Code, use:
```sql
SELECT * FROM teams;
SELECT * FROM players ORDER BY jersey_number;
```

---

## 🎯 Next: AI Jersey Detection

**Status:** Not yet implemented
**Priority:** High for sports photography use case

### What Needs to be Done:

1. **Update Gemini Prompt** (`backend/app/services/gemini_vision.py`)
   - Add team logo to analysis when team_mode=true
   - Add player roster to prompt
   - Request jersey number detection
   - Request player identification

2. **Update Analysis Endpoint** (`backend/app/api/analysis.py`)
   - Accept `team_id` parameter
   - Fetch team and players
   - Pass to Gemini service
   - Store detected_jersey_number in database

3. **Frontend Upload Flow**
   - Add "Team Mode" toggle to upload
   - Add team selector dropdown
   - Pass team_id to analysis API

4. **Gallery Enhancements**
   - Filter images by player
   - Show player names on image cards
   - Display jersey number detections

### Database Trigger (Already Working!)

The database automatically matches jersey numbers to players:
- When `detected_jersey_number` is set on an image
- And `team_id` is set
- And `team_mode_enabled` = true
- The trigger finds matching player and sets `player_id`

**File:** `database/migration_001_team_player_support.sql:207-228`

---

## 🐛 Troubleshooting

### Backend Issues

**Backend won't start:**
```bash
cd backend
pip install -r requirements.txt
pip install email-validator
```

**Can't connect to database:**
- Check `.env` DATABASE_URL is correct
- Verify Supabase project is active
- Test MCP connection: `/mcp` in Claude Code

### Frontend Issues

**Build errors:**
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

**Auth not working:**
- Check `.env.local` has correct Supabase keys
- Verify Google OAuth is enabled in Supabase
- Check callback URL: `http://localhost:3005/auth/callback`

**API calls failing:**
- Verify backend is running on port 8015
- Check browser console for errors
- Verify you're logged in (auth token exists)

### Database Issues

**Tables don't exist:**
```bash
python run_migrations.py
```

**RLS blocking queries:**
- Make sure you're authenticated
- Check RLS policies in Supabase dashboard

---

## 📋 Quick Links

- **Backend Health:** http://localhost:8015/health
- **API Docs:** http://localhost:8015/api/docs
- **Frontend:** http://localhost:3005
- **Settings:** http://localhost:3005/settings
- **Teams:** http://localhost:3005/settings/teams
- **Supabase:** https://supabase.com/dashboard
- **MCP Test:** Run `/mcp` in Claude Code

---

## ✨ What You Can Do Now

1. ✅ Create sports teams
2. ✅ Upload team logos
3. ✅ Set team colors
4. ✅ Manage player rosters
5. ✅ Track jersey numbers
6. ✅ Organize by sport/season
7. ✅ View all teams and players

## 🚧 Coming Next

1. ⏳ AI jersey number detection
2. ⏳ Player identification in photos
3. ⏳ Filter gallery by player
4. ⏳ Team logo matching
5. ⏳ Bulk player CSV import
6. ⏳ Player statistics

---

**Everything is ready! Start testing and let me know if you find any issues!**
