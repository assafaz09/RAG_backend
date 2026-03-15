from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import User
from app.schemas.auth import UserCreate, UserRead, Token, TokenData, GoogleOAuthUserInfo
from app.db.database import get_db


class AuthService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify JWT token and return token data"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            
            if user_id is None:
                return None
                
            token_data = TokenData(user_id=user_id, email=email)
            return token_data
        except JWTError:
            return None

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    def create_user_from_oauth(self, db: Session, oauth_user: GoogleOAuthUserInfo) -> User:
        """Create or update user from OAuth data"""
        user = self.get_user_by_email(db, oauth_user.email)
        
        if user:
            # Update existing user
            user.name = oauth_user.name
            user.profile_picture_url = oauth_user.picture
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                email=oauth_user.email,
                name=oauth_user.name,
                profile_picture_url=oauth_user.picture,
                is_active=True
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, oauth_user: GoogleOAuthUserInfo) -> Token:
        """Authenticate user with OAuth and return JWT token"""
        user = self.create_user_from_oauth(db, oauth_user)
        
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60
        )

    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        token_data = self.verify_token(token)
        if token_data is None:
            return None
        
        user = self.get_user_by_id(db, token_data.user_id)
        if user is None or not user.is_active:
            return None
            
        return user


auth_service = AuthService()
