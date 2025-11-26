"""
Player roster management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging
import csv
import io

from app.models.team import (
    Player, PlayerCreate, PlayerUpdate, PlayerListResponse,
    PlayerBulkCreate, PlayerImportCSV
)
from app.core.auth import get_current_user
from app.core.supabase import supabase_client

router = APIRouter(prefix="/players", tags=["players"])
logger = logging.getLogger(__name__)


async def verify_team_access(team_id: UUID, user_id: str, require_manage: bool = False):
    """
    Verify user has access to a team
    Returns team data if access is granted
    """
    # Get team
    team_response = supabase_client.table("teams").select("*").eq("id", str(team_id)).execute()

    if not team_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    team = team_response.data[0]

    # Check if user is owner
    if team["user_id"] == user_id:
        return team

    # Check team membership
    member_response = supabase_client.table("team_members").select("*").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

    if not member_response.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this team"
        )

    member = member_response.data[0]

    if require_manage and not member["can_manage_roster"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage this team's roster"
        )

    return team


@router.get("/team/{team_id}", response_model=PlayerListResponse)
async def list_team_players(
    team_id: UUID,
    current_user: dict = Depends(get_current_user),
    include_inactive: bool = False
):
    """
    Get all players for a team
    """
    try:
        user_id = current_user["id"]

        # Verify access
        await verify_team_access(team_id, user_id)

        # Get players
        query = supabase_client.table("players").select("*").eq("team_id", str(team_id))

        if not include_inactive:
            query = query.eq("is_active", True)

        query = query.order("jersey_number")
        response = query.execute()

        return {
            "players": response.data,
            "total": len(response.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing players for team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list players: {str(e)}"
        )


@router.post("/", response_model=Player, status_code=status.HTTP_201_CREATED)
async def create_player(
    player: PlayerCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new player
    """
    try:
        user_id = current_user["id"]

        # Verify access
        await verify_team_access(player.team_id, user_id, require_manage=True)

        # Check for duplicate jersey number
        existing = supabase_client.table("players").select("id").eq("team_id", str(player.team_id)).eq("jersey_number", player.jersey_number).eq("is_active", True).execute()

        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jersey number {player.jersey_number} is already assigned to another player on this team"
            )

        # Create player
        player_data = player.model_dump()
        # Convert UUID to string for Supabase
        player_data["team_id"] = str(player_data["team_id"])
        response = supabase_client.table("players").insert(player_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create player"
            )

        logger.info(f"Player created: {response.data[0]['id']} for team {player.team_id} by user {user_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating player: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create player: {str(e)}"
        )


@router.get("/{player_id}", response_model=Player)
async def get_player(
    player_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get player details
    """
    try:
        user_id = current_user["id"]

        # Get player
        player_response = supabase_client.table("players").select("*").eq("id", str(player_id)).execute()

        if not player_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )

        player = player_response.data[0]

        # Verify access to team
        await verify_team_access(UUID(player["team_id"]), user_id)

        return player

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player {player_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get player: {str(e)}"
        )


@router.patch("/{player_id}", response_model=Player)
async def update_player(
    player_id: UUID,
    player_update: PlayerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update player details
    """
    try:
        user_id = current_user["id"]

        # Get player
        player_response = supabase_client.table("players").select("*").eq("id", str(player_id)).execute()

        if not player_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )

        player = player_response.data[0]

        # Verify access
        await verify_team_access(UUID(player["team_id"]), user_id, require_manage=True)

        # Check for duplicate jersey number if changing
        if player_update.jersey_number and player_update.jersey_number != player["jersey_number"]:
            existing = supabase_client.table("players").select("id").eq("team_id", player["team_id"]).eq("jersey_number", player_update.jersey_number).eq("is_active", True).execute()

            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Jersey number {player_update.jersey_number} is already assigned to another player"
                )

        # Update player
        update_data = player_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        response = supabase_client.table("players").update(update_data).eq("id", str(player_id)).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update player"
            )

        logger.info(f"Player updated: {player_id} by user {user_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player {player_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update player: {str(e)}"
        )


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    player_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a player (soft delete by setting is_active=false)
    """
    try:
        user_id = current_user["id"]

        # Get player
        player_response = supabase_client.table("players").select("team_id").eq("id", str(player_id)).execute()

        if not player_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )

        player = player_response.data[0]

        # Verify access
        await verify_team_access(UUID(player["team_id"]), user_id, require_manage=True)

        # Soft delete (set is_active to false and clear jersey_number to free it up)
        supabase_client.table("players").update({
            "is_active": False,
            "jersey_number": None  # Clear jersey number to avoid unique constraint conflicts
        }).eq("id", str(player_id)).execute()

        logger.info(f"Player deleted: {player_id} by user {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting player {player_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete player: {str(e)}"
        )


@router.post("/bulk", response_model=PlayerListResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_players(
    bulk_create: PlayerBulkCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create multiple players at once
    """
    try:
        user_id = current_user["id"]

        # Verify access
        await verify_team_access(bulk_create.team_id, user_id, require_manage=True)

        # Check for duplicate jersey numbers
        jersey_numbers = [p.jersey_number for p in bulk_create.players]
        if len(jersey_numbers) != len(set(jersey_numbers)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate jersey numbers in the request"
            )

        # Check existing jersey numbers
        existing = supabase_client.table("players").select("jersey_number").eq("team_id", str(bulk_create.team_id)).eq("is_active", True).execute()

        existing_numbers = {p["jersey_number"] for p in existing.data}
        duplicate_numbers = existing_numbers.intersection(set(jersey_numbers))

        if duplicate_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jersey numbers already in use: {', '.join(duplicate_numbers)}"
            )

        # Create players
        players_data = [
            {**p.model_dump(), "team_id": str(bulk_create.team_id)}
            for p in bulk_create.players
        ]

        response = supabase_client.table("players").insert(players_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create players"
            )

        logger.info(f"Bulk created {len(response.data)} players for team {bulk_create.team_id} by user {user_id}")

        return {
            "players": response.data,
            "total": len(response.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk creating players: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create players: {str(e)}"
        )


@router.post("/import-csv", response_model=PlayerListResponse, status_code=status.HTTP_201_CREATED)
async def import_players_csv(
    import_data: PlayerImportCSV,
    current_user: dict = Depends(get_current_user)
):
    """
    Import players from CSV data
    Expected CSV format: jersey_number,first_name,last_name,position,grade_year
    """
    try:
        user_id = current_user["id"]

        # Verify access
        await verify_team_access(import_data.team_id, user_id, require_manage=True)

        # Parse CSV
        csv_file = io.StringIO(import_data.csv_data)
        reader = csv.DictReader(csv_file)

        players = []
        for row in reader:
            if not row.get("jersey_number") or not row.get("first_name") or not row.get("last_name"):
                continue  # Skip incomplete rows

            players.append(PlayerCreate(
                team_id=import_data.team_id,
                jersey_number=row["jersey_number"].strip(),
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                position=row.get("position", "").strip() or None,
                grade_year=row.get("grade_year", "").strip() or None,
                notes=row.get("notes", "").strip() or None
            ))

        if not players:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid players found in CSV data"
            )

        # Use bulk create
        bulk_response = await bulk_create_players(
            PlayerBulkCreate(team_id=import_data.team_id, players=players),
            current_user
        )

        logger.info(f"Imported {bulk_response['total']} players from CSV for team {import_data.team_id}")
        return bulk_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing players from CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import players: {str(e)}"
        )
