from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
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
