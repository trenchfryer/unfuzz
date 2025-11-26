"""
Authentication endpoints for user profile and session management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel, EmailStr
import logging

from app.core.auth import get_current_user
from app.core.supabase import supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    """User profile response"""
    id: str
    email: EmailStr
    subscription_tier: str = "free"
    total_images_processed: int = 0
    monthly_images_used: int = 0
    created_at: str
    user_metadata: Optional[dict] = None


class UserProfileUpdate(BaseModel):
    """Update user profile"""
    subscription_tier: Optional[str] = None


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user's profile

    This endpoint returns both Supabase auth data and user table data
    """
    try:
        user_id = current_user["id"]

        # Get user from database
        user_response = supabase_client.table("users").select("*").eq("id", user_id).execute()

        # If user doesn't exist in database, create them
        if not user_response.data:
            logger.info(f"Creating new user record for {user_id}")

            new_user = {
                "id": user_id,
                "email": current_user["email"],
                "subscription_tier": "free",
                "total_images_processed": 0,
                "monthly_images_used": 0
            }

            create_response = supabase_client.table("users").insert(new_user).execute()

            if not create_response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile"
                )

            user_data = create_response.data[0]
        else:
            user_data = user_response.data[0]

        return {
            **user_data,
            "user_metadata": current_user.get("user_metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.patch("/me", response_model=UserProfile)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current user's profile
    """
    try:
        user_id = current_user["id"]

        update_data = profile_update.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Update user in database
        response = supabase_client.table("users").update(update_data).eq("id", user_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

        logger.info(f"User profile updated: {user_id}")

        return {
            **response.data[0],
            "user_metadata": current_user.get("user_metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/session")
async def get_session_info(current_user: dict = Depends(get_current_user)):
    """
    Get current session information
    """
    return {
        "authenticated": True,
        "user_id": current_user["id"],
        "email": current_user["email"]
    }
