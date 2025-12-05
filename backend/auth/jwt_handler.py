"""
JWT token handling for authentication
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
import bcrypt
import secrets

from backend.config import settings


class JWTHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt directly"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash using bcrypt directly"""
        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key, 
            algorithm=settings.algorithm
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.JWTError:
            raise ValueError("Invalid token")
    
    @staticmethod
    def create_email_verification_token(email: str) -> str:
        """Create email verification token"""
        data = {"email": email, "type": "email_verification"}
        expire = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
        data.update({"exp": expire})
        
        return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
    
    @staticmethod
    def create_password_reset_token(email: str) -> str:
        """Create password reset token"""
        data = {"email": email, "type": "password_reset"}
        expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        data.update({"exp": expire})
        
        return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
    
    @staticmethod
    def verify_email_token(token: str) -> Optional[str]:
        """Verify email verification token and return email"""
        try:
            payload = JWTHandler.decode_token(token)
            if payload.get("type") != "email_verification":
                return None
            return payload.get("email")
        except ValueError:
            return None
    
    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """Verify password reset token and return email"""
        try:
            payload = JWTHandler.decode_token(token)
            if payload.get("type") != "password_reset":
                return None
            return payload.get("email")
        except ValueError:
            return None
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return f"vti_{secrets.token_urlsafe(32)}"  # vti = video text inpainting

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage using bcrypt"""
        return JWTHandler.hash_password(api_key)

    @staticmethod
    def verify_api_key(plain_key: str, hashed_key: str) -> bool:
        """Verify API key against its hash"""
        return JWTHandler.verify_password(plain_key, hashed_key)