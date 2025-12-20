"""
Pydantic schemas for Phraze.so integration
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CallbackStatus(str, Enum):
    """Status values for callback notifications"""
    STARTED = "started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubscriptionTier(str, Enum):
    """Subscription tier values from phraze.so"""
    FREE = "free"
    NORMAL = "normal"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PhrazeTokenPayload(BaseModel):
    """JWT token payload from phraze.so"""
    sub: str = Field(..., description="User ID from phraze.so")
    job_id: str = Field(..., description="Job ID from phraze.so")
    video_url: str = Field(..., description="S3 URL of video to edit")
    callback_url: str = Field(..., description="URL to call when processing completes")
    permissions: list[str] = Field(default=["edit", "process"], description="Permissions")
    subscription_tier: str = Field(default="normal", description="User subscription tier: free, normal, pro, enterprise")
    iat: int = Field(..., description="Issued at timestamp")
    exp: int = Field(..., description="Expiration timestamp")

    @property
    def user_id(self) -> str:
        """Alias for sub field"""
        return self.sub

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow().timestamp() > self.exp

    @property
    def is_pro_user(self) -> bool:
        """Check if user has pro or higher subscription"""
        return self.subscription_tier in ["pro", "enterprise"]


class PhrazeCallbackPayload(BaseModel):
    """Callback payload sent to phraze.so"""
    job_id: str = Field(..., description="Job ID from phraze.so")
    status: CallbackStatus = Field(..., description="Current job status")
    output_url: Optional[str] = Field(None, description="S3 URL of processed video")
    processing_time_seconds: Optional[int] = Field(None, description="Time taken to process")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Callback timestamp")
    signature: Optional[str] = Field(None, description="HMAC signature for verification")


class ValidationResponse(BaseModel):
    """Response for token validation"""
    valid: bool
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    video_url: Optional[str] = None
    callback_url: Optional[str] = None
    subscription_tier: Optional[str] = None
    is_pro_user: bool = False
    message: str


class ProcessRequest(BaseModel):
    """Request body for processing video"""
    processing_type: str = Field(default="text_removal", description="Type: text_removal, lip_sync, both")
    target_language: Optional[str] = Field(None, description="Target language for lip-sync")
    audio_url: Optional[str] = Field(None, description="Audio URL for lip-sync")
    segments: Optional[list[dict]] = Field(None, description="Segments for pro lip-sync")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error_code: str
    message: str
    redirect_url: Optional[str] = None
    job_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
