"""
Users routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from backend.models.database import get_database
from backend.models.user import User, CreditTransaction, APIKey, SubscriptionTier
from backend.models.job import VideoJob, JobStatus
from backend.auth.dependencies import get_current_user
from backend.auth.jwt_handler import JWTHandler
from sqlalchemy import func
from .schemas import (
    UserResponse, UserProfile, UserStatsResponse,
    APIKeyResponse, APIKeyCreate, CreditTransactionResponse
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        company=current_user.company,
        email_verified=current_user.email_verified,
        subscription_tier=current_user.subscription_tier.name,
        credits_balance=current_user.credits_balance,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )

@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Get user statistics"""

    # Get job counts by status
    total_jobs = db.query(VideoJob).filter(VideoJob.user_id == current_user.id).count()
    pending_jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id,
        VideoJob.status.in_([JobStatus.QUEUED, JobStatus.UPLOADING])
    ).count()
    processing_jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id,
        VideoJob.status == JobStatus.PROCESSING
    ).count()
    completed_jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id,
        VideoJob.status == JobStatus.COMPLETED
    ).count()
    failed_jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id,
        VideoJob.status == JobStatus.FAILED
    ).count()

    # Calculate success rate
    total_finished = completed_jobs + failed_jobs
    success_rate = (completed_jobs / total_finished * 100) if total_finished > 0 else 0.0

    # Get credits used this month (simplified - using total used credits for now)
    credits_used = db.query(func.coalesce(func.sum(CreditTransaction.amount), 0)).filter(
        CreditTransaction.user_id == current_user.id,
        CreditTransaction.transaction_type == "debit"
    ).scalar()

    return UserStatsResponse(
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        processing_jobs=processing_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        success_rate=round(success_rate, 1),
        credits_used_this_month=abs(credits_used) if credits_used else 0,
        monthly_credit_limit=current_user.subscription_tier.credits_per_month
    )

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Update current user profile"""

    # Update profile fields
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.company is not None:
        current_user.company = profile_data.company

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        company=current_user.company,
        email_verified=current_user.email_verified,
        subscription_tier=current_user.subscription_tier.name,
        credits_balance=current_user.credits_balance,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )

@router.get("/me/credits", response_model=List[CreditTransactionResponse])
async def get_credit_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Get user's credit transaction history"""

    transactions = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == current_user.id
    ).order_by(
        CreditTransaction.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        CreditTransactionResponse(
            id=t.id,
            transaction_type=t.transaction_type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            created_at=t.created_at
        )
        for t in transactions
    ]

@router.get("/me/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Get user's API keys"""

    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(APIKey.created_at.desc()).all()

    return [
        APIKeyResponse(
            id=key.id,
            key_name=key.key_name,
            api_key_prefix=key.api_key_prefix,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            total_requests=key.total_requests
        )
        for key in api_keys
    ]

@router.post("/me/api-keys", response_model=dict)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Create a new API key"""

    # Check if user already has too many API keys
    existing_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()

    if existing_keys >= 5:  # Limit to 5 active API keys
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys reached (5)"
        )

    # Create new API key
    api_key_record, plain_key = APIKey.create_api_key(
        user_id=current_user.id,
        key_name=key_data.key_name
    )

    db.add(api_key_record)
    db.commit()

    return {
        "api_key": plain_key,
        "key_name": key_data.key_name,
        "message": "API key created successfully. Save this key securely - it won't be shown again."
    }
