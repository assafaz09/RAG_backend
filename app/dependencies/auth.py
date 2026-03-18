from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.supabase_auth import supabase_auth_service
from app.db.models import User
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user using Supabase JWT"""
    token = credentials.credentials
    
    logger.info(f"🔍 [AUTH] Attempting to authenticate user")
    logger.info(f"🔍 [AUTH] Token received: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
    
    user = supabase_auth_service.get_current_user(db, token)
    
    logger.info(f"🔍 [AUTH] User lookup result: {user}")
    
    if user is None:
        logger.warning(f"❌ [AUTH] Authentication failed - user not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"✅ [AUTH] Authentication successful for user: {user.id}")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    if credentials is None:
        return None
    
    token = credentials.credentials
    return supabase_auth_service.get_current_user(db, token)
