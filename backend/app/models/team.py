"""
Pydantic models for teams and players
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Team Models
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Team name")
    sport: Optional[str] = Field(None, max_length=100, description="Sport type (basketball, soccer, etc.)")
    season: Optional[str] = Field(None, max_length=100, description="Season (2024-2025, Spring 2024, etc.)")
    # Deprecated - use home_* fields instead
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Primary color hex code (deprecated)")
    secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Secondary color hex code (deprecated)")
    # Home jersey colors
    home_primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Home jersey primary color")
    home_secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Home jersey secondary color")
    home_tertiary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Home jersey tertiary color")
    # Away jersey colors
    away_primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Away jersey primary color")
    away_secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Away jersey secondary color")
    away_tertiary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Away jersey tertiary color")
    notes: Optional[str] = None


class TeamCreate(TeamBase):
    """Create team request"""
    pass


class TeamUpdate(BaseModel):
    """Update team request - all fields optional"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sport: Optional[str] = Field(None, max_length=100)
    season: Optional[str] = Field(None, max_length=100)
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    # Home jersey colors
    home_primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    home_secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    home_tertiary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    # Away jersey colors
    away_primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    away_secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    away_tertiary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class Team(TeamBase):
    """Team response"""
    id: UUID
    user_id: UUID
    # Deprecated logo fields
    logo_url: Optional[str] = None
    logo_storage_path: Optional[str] = None
    # Home and away logo fields
    home_logo_url: Optional[str] = None
    home_logo_storage_path: Optional[str] = None
    away_logo_url: Optional[str] = None
    away_logo_storage_path: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Temporarily commented out due to forward reference issues
# class TeamWithPlayers(Team):
#     """Team response with players list"""
#     players: List['Player'] = []
#     player_count: int = 0


# Player Models
class PlayerBase(BaseModel):
    jersey_number: str = Field(..., min_length=1, max_length=10, description="Jersey number (can be 12, 3A, etc.)")
    first_name: str = Field(..., min_length=1, max_length=100, description="Player first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Player last name")
    position: Optional[str] = Field(None, max_length=50, description="Player position")
    grade_year: Optional[str] = Field(None, max_length=20, description="Grade/year (Freshman, 9th, etc.)")
    notes: Optional[str] = None


class PlayerCreate(PlayerBase):
    """Create player request"""
    team_id: UUID


class PlayerUpdate(BaseModel):
    """Update player request - all fields optional"""
    jersey_number: Optional[str] = Field(None, min_length=1, max_length=10)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[str] = Field(None, max_length=50)
    grade_year: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class Player(PlayerBase):
    """Player response"""
    id: UUID
    team_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlayerWithTeam(Player):
    """Player response with team information"""
    team: Optional[Team] = None


# Team Member Models
class TeamMemberBase(BaseModel):
    role: str = Field("viewer", description="Role: owner, admin, editor, viewer")
    can_view: bool = True
    can_edit: bool = False
    can_manage_roster: bool = False
    can_manage_members: bool = False


class TeamMemberInvite(TeamMemberBase):
    """Invite team member request"""
    user_email: str = Field(..., description="Email of user to invite")
    team_id: UUID


class TeamMemberUpdate(BaseModel):
    """Update team member permissions"""
    role: Optional[str] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_manage_roster: Optional[bool] = None
    can_manage_members: Optional[bool] = None
    status: Optional[str] = None


class TeamMember(TeamMemberBase):
    """Team member response"""
    id: UUID
    team_id: UUID
    user_id: UUID
    invited_by: Optional[UUID] = None
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Bulk Operations
class PlayerBulkCreate(BaseModel):
    """Bulk create players"""
    team_id: UUID
    players: List[PlayerBase]


class PlayerImportCSV(BaseModel):
    """Import players from CSV data"""
    team_id: UUID
    csv_data: str = Field(..., description="CSV data with columns: jersey_number,first_name,last_name,position,grade_year")


# Response Models
class TeamListResponse(BaseModel):
    """List of teams response"""
    teams: List[Team]
    total: int


class PlayerListResponse(BaseModel):
    """List of players response"""
    players: List[Player]
    total: int


class TeamMemberListResponse(BaseModel):
    """List of team members response"""
    members: List[TeamMember]
    total: int
