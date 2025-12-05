"""
Authentication business logic handlers
"""

from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from typing import Tuple

from backend.models.user import User, UserSession, SubscriptionTier
from backend.auth.jwt_handler import JWTHandler
from backend.config import settings
from .schemas import (
    UserRegister, UserLogin, TokenRefresh, PasswordReset,
    PasswordResetConfirm, EmailVerification, UserResponse
)
async def handle_logout(user: User, db: Session) -> None:
    """Handle user logout by invalidating all sessions"""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id
    ).all()

    for session in sessions:
        db.delete(session)

    db.commit()


async def handle_email_verification(
    verification_data: EmailVerification,
    db: Session
) -> None:
    """Handle email verification"""
    email = JWTHandler.verify_email_token(verification_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Verify email
    user.email_verified = True
    user.email_verification_token = None
    db.commit()


async def handle_password_reset_request(
    reset_data: PasswordReset,
    db: Session
) -> None:
    """Handle password reset request"""
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user:
        # Don't reveal if email exists
        return

    # Generate reset token
    reset_token = JWTHandler.create_password_reset_token(user.email)
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)

    db.commit()

    # TODO: Send password reset email
    # await send_password_reset_email(user.email, reset_token)


async def handle_password_reset_confirm(
    reset_data: PasswordResetConfirm,
    db: Session
) -> None:
    """Handle password reset confirmation"""
    email = JWTHandler.verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Reset password
    user.set_password(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None

    # Invalidate all existing sessions
    sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()
    for session in sessions:
        db.delete(session)

    db.commit()


def _create_user_session(
    db: Session,
    user: User,
    request: Request
) -> Tuple[str, str]:
    """
    Create user session and generate tokens
    Returns: (access_token, refresh_token)
    """
    session = UserSession.create_session(
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    db.add(session)

    # Create tokens
    access_token = JWTHandler.create_access_token({"sub": str(user.id)})
    refresh_token = JWTHandler.create_refresh_token({"sub": str(user.id)})

    # Update session with tokens
    session.session_token = access_token
    session.refresh_token = refresh_token

    return access_token, refresh_token


def _build_user_response(user: User) -> UserResponse:
    """Build UserResponse from User model"""
    # Handle case where subscription_tier might not be loaded
    tier_name = "free"
    if user.subscription_tier:
        tier_name = user.subscription_tier.name

    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        company=user.company,
        email_verified=user.email_verified,
        subscription_tier=tier_name,
        credits_balance=user.credits_balance,
        created_at=user.created_at
    )
