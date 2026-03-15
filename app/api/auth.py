from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth import auth_service
from app.schemas.auth import Token, UserRead
from app.db.models import User
from app.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])



@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout():
    """Logout user (client-side token invalidation)"""
    # In a real implementation, you might want to:
    # 1. Add the token to a blacklist
    # 2. Set a shorter expiration time
    # 3. Clear server-side session data
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        # Create new token for the current user
        token = auth_service.authenticate_user(db, current_user)
        return token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )
