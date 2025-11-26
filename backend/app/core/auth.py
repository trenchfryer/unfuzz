"""
Authentication middleware and utilities for verifying Supabase JWTs
"""
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from app.core.supabase import supabase_client
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify Supabase JWT token

    Returns:
        dict: User information from the token

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    logger.info(f"🔑 Verifying token: {token[:20]}...")

    try:
        # Verify the token with Supabase
        user_response = supabase_client.auth.get_user(token)
        logger.info(f"✅ User response received")

        if not user_response or not user_response.user:
            logger.error("❌ No user found in response")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = user_response.user

        return {
            "id": user.id,
            "email": user.email,
            "user_metadata": user.user_metadata,
            "app_metadata": user.app_metadata,
        }

    except jwt.ExpiredSignatureError as e:
        logger.error(f"❌ Token expired: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"❌ Token verification error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(user_data: dict = Depends(verify_token)) -> dict:
    """
    Get current authenticated user

    This is a convenience dependency that can be used in route handlers
    to get the current user.

    Usage:
        @router.get("/me")
        async def get_me(current_user: dict = Depends(get_current_user)):
            return current_user
    """
    return user_data


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None

    This is useful for endpoints that have optional authentication.
    """
    if not credentials:
        return None

    try:
        return await verify_token(credentials)
    except HTTPException:
        return None
