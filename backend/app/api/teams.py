"""
Team management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from uuid import UUID
import logging

from app.models.team import (
    Team, TeamCreate, TeamUpdate, TeamListResponse
)
from app.core.auth import get_current_user
from app.core.supabase import supabase_client

router = APIRouter(prefix="/teams", tags=["teams"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=TeamListResponse)
async def list_teams(
    current_user: dict = Depends(get_current_user),
    include_inactive: bool = False
):
    """
    Get all teams for the current user (owned or member of)
    """
    try:
        user_id = current_user["id"]

        # Build query - filter by user ownership
        query = supabase_client.table("teams").select("*").eq("user_id", user_id)

        if not include_inactive:
            query = query.eq("is_active", True)

        query = query.order("created_at", desc=True)

        response = query.execute()

        return {
            "teams": response.data,
            "total": len(response.data)
        }

    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list teams: {str(e)}"
        )


@router.post("/", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    team: TeamCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new team
    """
    try:
        user_id = current_user["id"]

        team_data = team.model_dump()
        team_data["user_id"] = user_id

        response = supabase_client.table("teams").insert(team_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create team"
            )

        logger.info(f"Team created: {response.data[0]['id']} by user {user_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}"
        )


@router.get("/{team_id}")
async def get_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get team details with players
    """
    try:
        user_id = current_user["id"]

        # Get team and verify access
        team_response = supabase_client.table("teams").select("*").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        team = team_response.data[0]

        # Verify user has access (owner or member)
        if team["user_id"] != user_id:
            # Check if user is a team member
            member_response = supabase_client.table("team_members").select("id").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this team"
                )

        # Get players
        players_response = supabase_client.table("players").select("*").eq("team_id", str(team_id)).eq("is_active", True).order("jersey_number").execute()

        return {
            **team,
            "players": players_response.data,
            "player_count": len(players_response.data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get team: {str(e)}"
        )


@router.patch("/{team_id}", response_model=Team)
async def update_team(
    team_id: UUID,
    team_update: TeamUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update team details
    """
    try:
        user_id = current_user["id"]

        # Verify ownership or admin access
        team_response = supabase_client.table("teams").select("*").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        team = team_response.data[0]

        # Check if user is owner or has manage_roster permission
        if team["user_id"] != user_id:
            member_response = supabase_client.table("team_members").select("can_manage_roster").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data or not member_response.data[0]["can_manage_roster"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to update this team"
                )

        # Update team
        update_data = team_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        response = supabase_client.table("teams").update(update_data).eq("id", str(team_id)).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update team"
            )

        logger.info(f"Team updated: {team_id} by user {user_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update team: {str(e)}"
        )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a team (only owner can delete)
    """
    try:
        user_id = current_user["id"]

        # Verify ownership
        team_response = supabase_client.table("teams").select("user_id").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        if team_response.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the team owner can delete the team"
            )

        # Delete team (cascade will delete players and members)
        supabase_client.table("teams").delete().eq("id", str(team_id)).execute()

        logger.info(f"Team deleted: {team_id} by user {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team: {str(e)}"
        )


@router.post("/{team_id}/logo")
async def upload_team_logo(
    team_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload team logo
    """
    try:
        user_id = current_user["id"]

        # Verify access
        team_response = supabase_client.table("teams").select("user_id").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        if team_response.data[0]["user_id"] != user_id:
            member_response = supabase_client.table("team_members").select("can_manage_roster").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data or not member_response.data[0]["can_manage_roster"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to upload team logo"
                )

        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Upload to Supabase Storage
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "png"
        storage_path = f"team-logos/{team_id}.{file_ext}"

        file_bytes = await file.read()

        # Upload to storage bucket
        upload_response = supabase_client.storage.from_("team-logos").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )

        # Get public URL
        public_url = supabase_client.storage.from_("team-logos").get_public_url(storage_path)

        # Update team record
        update_response = supabase_client.table("teams").update({
            "logo_url": public_url,
            "logo_storage_path": storage_path
        }).eq("id", str(team_id)).execute()

        logger.info(f"Team logo uploaded: {team_id} by user {user_id}")

        return {
            "logo_url": public_url,
            "storage_path": storage_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading team logo for {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload team logo: {str(e)}"
        )


@router.delete("/{team_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_logo(
    team_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete team logo
    """
    try:
        user_id = current_user["id"]

        # Verify access
        team_response = supabase_client.table("teams").select("user_id, logo_storage_path").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        team = team_response.data[0]

        if team["user_id"] != user_id:
            member_response = supabase_client.table("team_members").select("can_manage_roster").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data or not member_response.data[0]["can_manage_roster"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete team logo"
                )

        # Delete from storage if exists
        if team["logo_storage_path"]:
            supabase_client.storage.from_("team-logos").remove([team["logo_storage_path"]])

        # Update team record
        supabase_client.table("teams").update({
            "logo_url": None,
            "logo_storage_path": None
        }).eq("id", str(team_id)).execute()

        logger.info(f"Team logo deleted: {team_id} by user {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team logo for {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team logo: {str(e)}"
        )


@router.post("/{team_id}/logo/home")
async def upload_home_jersey_logo(
    team_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload home jersey logo and automatically extract team colors
    """
    try:
        import tempfile
        import os
        from app.services.color_extraction import extract_team_colors

        user_id = current_user["id"]

        # Verify access
        team_response = supabase_client.table("teams").select("user_id").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        if team_response.data[0]["user_id"] != user_id:
            member_response = supabase_client.table("team_members").select("can_manage_roster").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data or not member_response.data[0]["can_manage_roster"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to upload team logo"
                )

        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        file_bytes = await file.read()

        # Save to temp file for color extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            # Extract colors from logo
            colors = extract_team_colors(temp_path)
            logger.info(f"Extracted home jersey colors: {colors}")
        finally:
            # Clean up temp file
            os.unlink(temp_path)

        # Upload to Supabase Storage
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "png"
        storage_path = f"team-logos/{team_id}_home.{file_ext}"

        # Upload to storage bucket
        upload_response = supabase_client.storage.from_("team-logos").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )

        # Get public URL
        public_url = supabase_client.storage.from_("team-logos").get_public_url(storage_path)

        # Update team record with logo and colors
        update_data = {
            "home_logo_url": public_url,
            "home_logo_storage_path": storage_path,
            "home_primary_color": colors["primary_color"],
            "home_secondary_color": colors["secondary_color"],
            "home_tertiary_color": colors["tertiary_color"]
        }

        update_response = supabase_client.table("teams").update(update_data).eq("id", str(team_id)).execute()

        logger.info(f"Home jersey logo uploaded for team {team_id} by user {user_id}")

        return {
            "logo_url": public_url,
            "storage_path": storage_path,
            "colors": colors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading home jersey logo for {team_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload home jersey logo: {str(e)}"
        )


@router.post("/{team_id}/logo/away")
async def upload_away_jersey_logo(
    team_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload away jersey logo and automatically extract team colors
    """
    try:
        import tempfile
        import os
        from app.services.color_extraction import extract_team_colors

        user_id = current_user["id"]

        # Verify access
        team_response = supabase_client.table("teams").select("user_id").eq("id", str(team_id)).execute()

        if not team_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        if team_response.data[0]["user_id"] != user_id:
            member_response = supabase_client.table("team_members").select("can_manage_roster").eq("team_id", str(team_id)).eq("user_id", user_id).eq("status", "active").execute()

            if not member_response.data or not member_response.data[0]["can_manage_roster"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to upload team logo"
                )

        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        file_bytes = await file.read()

        # Save to temp file for color extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            # Extract colors from logo
            colors = extract_team_colors(temp_path)
            logger.info(f"Extracted away jersey colors: {colors}")
        finally:
            # Clean up temp file
            os.unlink(temp_path)

        # Upload to Supabase Storage
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "png"
        storage_path = f"team-logos/{team_id}_away.{file_ext}"

        # Upload to storage bucket
        upload_response = supabase_client.storage.from_("team-logos").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )

        # Get public URL
        public_url = supabase_client.storage.from_("team-logos").get_public_url(storage_path)

        # Update team record with logo and colors
        update_data = {
            "away_logo_url": public_url,
            "away_logo_storage_path": storage_path,
            "away_primary_color": colors["primary_color"],
            "away_secondary_color": colors["secondary_color"],
            "away_tertiary_color": colors["tertiary_color"]
        }

        update_response = supabase_client.table("teams").update(update_data).eq("id", str(team_id)).execute()

        logger.info(f"Away jersey logo uploaded for team {team_id} by user {user_id}")

        return {
            "logo_url": public_url,
            "storage_path": storage_path,
            "colors": colors
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading away jersey logo for {team_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload away jersey logo: {str(e)}"
        )
