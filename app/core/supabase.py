"""
Supabase client configuration and utilities
"""
from typing import Optional, Dict, Any
from supabase.client import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Singleton Supabase client manager"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._admin_client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Get Supabase client with anon key"""
        if self._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
                raise ValueError("Supabase URL and ANON_KEY must be set")
            
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            logger.info("Supabase client initialized")
        
        return self._client
    
    @property
    def admin_client(self) -> Client:
        """Get Supabase client with service role key (for admin operations)"""
        if self._admin_client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError("Supabase URL and SERVICE_ROLE_KEY must be set")
            
            self._admin_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("Supabase admin client initialized")
        
        return self._admin_client
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret for token verification"""
        if not settings.SUPABASE_JWT_SECRET:
            # In production, this should be set in environment
            # For development, we can extract it from the service role key
            logger.warning("SUPABASE_JWT_SECRET not set, using service role key")
            return settings.SUPABASE_SERVICE_ROLE_KEY or ""
        return settings.SUPABASE_JWT_SECRET

# Global instance
supabase = SupabaseClient()

def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Supabase JWT token and return the user claims
    """
    logger.info(f"🔍 [SUPABASE_CORE] Verifying token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
    
    try:
        import jwt
        from datetime import datetime
        
        # Get the appropriate key based on algorithm
        if settings.SUPABASE_JWT_ALGORITHM == "ES256":
            # For ES256, use the public key in proper PEM format
            import base64
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            
            # Convert the JWK to proper PEM format
            x = "sFd0hg3R_nQPqqPUh5N_fy0anLqQ7viKbd4v7Rz5naw"
            y = "eOZX1st4zL8koo3fQIE2fwp28GZzeolGZcVLiehjqvQ"
            
            # Create the public key object
            public_key = ec.EllipticCurvePublicNumbers(
                curve=ec.SECP256R1(),
                x=int.from_bytes(base64.urlsafe_b64decode(x + '=' * (-len(x) % 4)), 'big'),
                y=int.from_bytes(base64.urlsafe_b64decode(y + '=' * (-len(y) % 4)), 'big')
            ).public_key()
            
            # Convert to PEM format
            jwt_key = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            logger.info(f"🔍 [SUPABASE_CORE] Using ES256 with public key")
        else:
            # For HS256, use the secret
            jwt_key = supabase.get_jwt_secret()
            logger.info(f"🔍 [SUPABASE_CORE] Using HS256 with secret")
        
        logger.info(f"🔍 [SUPABASE_CORE] Key preview: {jwt_key[:50] if jwt_key and len(jwt_key) > 50 else jwt_key}")
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            jwt_key,
            algorithms=[settings.SUPABASE_JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_aud": False  # Disable audience validation for now
            }
        )
        
        logger.info(f"🔍 [SUPABASE_CORE] Decoded payload: {payload}")
        
        # Check expiration
        exp = payload.get('exp')
        if exp and datetime.utcnow().timestamp() > exp:
            logger.warning(f"❌ [SUPABASE_CORE] Token expired: {exp} vs {datetime.utcnow().timestamp()}")
            return None
        
        logger.info(f"✅ [SUPABASE_CORE] Token verified successfully")
        return payload
        
    except Exception as e:
        logger.error(f"❌ [SUPABASE_CORE] Token verification failed: {e}")
        import traceback
        logger.error(f"❌ [SUPABASE_CORE] Traceback: {traceback.format_exc()}")
        return None

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from Supabase token
    """
    payload = verify_supabase_token(token)
    if not payload:
        return None
    
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("user_metadata", {}).get("name"),
        "picture": payload.get("user_metadata", {}).get("picture"),
        "role": payload.get("role", "authenticated")
    }
