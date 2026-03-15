from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import UserRead, UserUpdate
from app.db.models import User
from app.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=UserRead)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get user profile"""
    return current_user


@router.put("/profile", response_model=UserRead)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete("/account")
async def delete_user_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user account"""
    # Soft delete by setting is_active to False
    current_user.is_active = False
    db.commit()
    
    return {"message": "Account deleted successfully"}
