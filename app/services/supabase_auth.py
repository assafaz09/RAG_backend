"""
Supabase Authentication Service
Handles user authentication and management with Supabase
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.supabase import supabase, get_user_from_token
from app.db.models import User
from app.schemas.auth import UserRead, TokenData
import logging
import uuid

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """Service for handling Supabase authentication"""
    
    def __init__(self):
        self.supabase_client = supabase
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify Supabase JWT token and return token data
        """
        logger.info(f"🔍 [SUPABASE_AUTH] Verifying token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
        
        try:
            # Extract user claims from token
            user_claims = get_user_from_token(token)
            logger.info(f"🔍 [SUPABASE_AUTH] User claims from token: {user_claims}")
            
            if not user_claims:
                logger.warning(f"❌ [SUPABASE_AUTH] No user claims found in token")
                return None
            
            token_data = TokenData(
                user_id=user_claims["id"],
                email=user_claims["email"],
                token=token  # Store the original token
            )
            
            logger.info(f"✅ [SUPABASE_AUTH] Token verified successfully for user: {token_data.user_id}")
            return token_data
            
        except Exception as e:
            logger.error(f"❌ [SUPABASE_AUTH] Token verification failed: {e}")
            import traceback
            logger.error(f"❌ [SUPABASE_AUTH] Traceback: {traceback.format_exc()}")
            return None
    
    def get_user_by_token(self, db: Session, token: str) -> Optional[User]:
        """
        Get user from Supabase JWT token
        """
        token_data = self.verify_token(token)
        if not token_data:
            return None
        
        # Try to get user from database
        user = db.query(User).filter(User.auth_provider_id == token_data.user_id).first()
        
        if not user:
            # Create user if doesn't exist (sync from Supabase)
            user = self._sync_user_from_token(db, token_data)
        
        return user
    
    def _sync_user_from_token(self, db: Session, token_data: TokenData) -> User:
        """
        Sync user from Supabase token to local database
        """
        try:
            logger.info(f"🔍 [SUPABASE_AUTH] Syncing user from token: {token_data}")
            # Get user details from Supabase - use the original token, not user_id
            user_claims = get_user_from_token(token_data.token)
            logger.info(f"🔍 [SUPABASE_AUTH] User claims: {user_claims}")
            if not user_claims:
                raise ValueError("Invalid token data")
            
            # Create new user
            user = User(
                email=token_data.email,
                name=user_claims.get("name", token_data.email.split("@")[0]),
                profile_picture_url=user_claims.get("picture"),
                auth_provider="supabase",
                auth_provider_id=token_data.user_id,
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Created new user: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to sync user: {e}")
            db.rollback()
            raise
    
    def create_or_update_user(self, db: Session, user_data: Dict[str, Any]) -> User:
        """
        Create or update user from Supabase auth data
        """
        try:
            # Check if user exists by auth provider ID
            user = db.query(User).filter(
                User.auth_provider_id == user_data["id"]
            ).first()
            
            if user:
                # Update existing user
                user.name = user_data.get("name", user.name)
                user.profile_picture_url = user_data.get("picture")
                user.email = user_data.get("email", user.email)
                user.updated_at = datetime.utcnow()
            else:
                # Create new user
                user = User(
                    email=user_data["email"],
                    name=user_data.get("name", user_data["email"].split("@")[0]),
                    profile_picture_url=user_data.get("picture"),
                    auth_provider="supabase",
                    auth_provider_id=user_data["id"],
                    is_active=True
                )
                db.add(user)
            
            db.commit()
            db.refresh(user)
            return user
            
        except Exception as e:
            logger.error(f"Failed to create/update user: {e}")
            db.rollback()
            raise
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """
        Get current authenticated user from token
        """
        return self.get_user_by_token(db, token)
    
    def logout_user(self, token: str) -> bool:
        """
        Logout user (invalidate session)
        Note: In Supabase, token invalidation is handled client-side
        """
        try:
            # For server-side logout, you could maintain a blacklist
            # but Supabase handles this automatically with JWT expiration
            logger.info(f"User logout requested for token")
            return True
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

# Create global instance
supabase_auth_service = SupabaseAuthService()
