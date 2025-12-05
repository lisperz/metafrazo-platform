"""
Pydantic schemas for authentication routes
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    """User registration request schema"""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None


class UserLogin(BaseModel):
    """User login request schema"""
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """Password reset request schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str


class EmailVerification(BaseModel):
    """Email verification request schema"""
    token: str


class TokenRefresh(BaseModel):
    """Token refresh request schema"""
    refresh_token: str


class UserResponse(BaseModel):
    """User information response schema"""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    email_verified: bool = False
    subscription_tier: str = "free"
    credits_balance: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
