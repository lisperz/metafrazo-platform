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
from .password_handlers import _create_user_session, _build_user_response


async def handle_user_registration(
    user_data: UserRegister,
    request: Request,
    db: Session
) -> Tuple[str, str, UserResponse]:
    """
    Handle user registration logic
    Returns: (access_token, refresh_token, user_response)
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Get default subscription tier (free)
    default_tier = db.query(SubscriptionTier).filter(
        SubscriptionTier.name == "free"
    ).first()

    if not default_tier:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default subscription tier not found"
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        company=user_data.company,
        subscription_tier_id=default_tier.id,
        credits_balance=settings.default_credits_new_user
    )

    # Set password and generate verification token
    new_user.set_password(user_data.password)
    verification_token = new_user.generate_email_verification_token()

    # Save user
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create session and tokens
    access_token, refresh_token = _create_user_session(
        db, new_user, request
    )

    # TODO: Send verification email
    # await send_verification_email(new_user.email, verification_token)

    user_response = _build_user_response(new_user)
    return access_token, refresh_token, user_response


async def handle_user_login(
    login_data: UserLogin,
    request: Request,
    db: Session
) -> Tuple[str, str, UserResponse]:
    """
    Handle user login logic
    Returns: (access_token, refresh_token, user_response)
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not user.check_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )

    # Update login information
    user.last_login_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1

    # Create session and tokens
    access_token, refresh_token = _create_user_session(
        db, user, request
    )

    db.commit()

    user_response = _build_user_response(user)
    return access_token, refresh_token, user_response


async def handle_token_refresh(
    token_data: TokenRefresh,
    db: Session
) -> Tuple[str, str, UserResponse]:
    """
    Handle token refresh logic
    Returns: (new_access_token, new_refresh_token, user_response)
    """
    try:
        # Decode refresh token
        payload = JWTHandler.decode_token(token_data.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Find user and session
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.refresh_token == token_data.refresh_token
        ).first()

        if not session or not session.is_valid():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Create new tokens
        new_access_token = JWTHandler.create_access_token({"sub": str(user.id)})
        new_refresh_token = JWTHandler.create_refresh_token({"sub": str(user.id)})

        # Update session
        session.session_token = new_access_token
        session.refresh_token = new_refresh_token
        session.refresh()

        db.commit()

        user_response = _build_user_response(user)
        return new_access_token, new_refresh_token, user_response

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


