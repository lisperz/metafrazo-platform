"""
Authentication routes for user registration, login, and token management
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from backend.models.database import get_database
from backend.models.user import User
from backend.auth.dependencies import get_current_user
from backend.config import settings
from .schemas import (
    UserRegister, UserLogin, TokenRefresh, PasswordReset,
    PasswordResetConfirm, EmailVerification, UserResponse, TokenResponse
)
from .handlers import (
    handle_user_registration, handle_user_login, handle_token_refresh,
    handle_logout, handle_email_verification, handle_password_reset_request,
    handle_password_reset_confirm, _build_user_response
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_database)
):
    """Register a new user account"""
    access_token, refresh_token, user_response = await handle_user_registration(
        user_data, request, db
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_response
    )


@router.post("/login")
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_database)
):
    """Login user and return JWT tokens"""
    try:
        access_token, refresh_token, user_response = await handle_user_login(
            login_data, request, db
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=user_response
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Login error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_database)
):
    """Refresh access token using refresh token"""
    new_access_token, new_refresh_token, user_response = await handle_token_refresh(
        token_data, db
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_response
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Logout user and invalidate session"""
    await handle_logout(current_user, db)
    return {"message": "Successfully logged out"}


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: Session = Depends(get_database)
):
    """Verify user email address"""
    await handle_email_verification(verification_data, db)
    return {"message": "Email verified successfully"}


@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordReset,
    db: Session = Depends(get_database)
):
    """Request password reset"""
    await handle_password_reset_request(reset_data, db)
    return {"message": "If an account with that email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_database)
):
    """Confirm password reset with new password"""
    await handle_password_reset_confirm(reset_data, db)
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return _build_user_response(current_user)
