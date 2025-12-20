"""
Video job processing models
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .database import Base

class JobStatus(enum.Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Job identification
    original_filename = Column(String(500), nullable=False)
    display_name = Column(String(500))

    # Job status and progress
    status = Column(String(20), default=JobStatus.QUEUED.value)
    progress_percentage = Column(Integer, default=0)
    progress_message = Column(Text)

    # Processing configuration
    processing_config = Column(JSONB, default=dict)
    zhaoli_task_id = Column(String(255))
    estimated_credits = Column(Integer)
    actual_credits_used = Column(Integer)

    # Pro Video Editor Support
    is_pro_job = Column(Boolean, default=False)  # True for Pro editor jobs
    segments_data = Column(JSONB, default=None)  # Segment configurations for Pro jobs

    # Embedded Mode Support (for phraze.so integration)
    is_embedded_job = Column(Boolean, default=False)  # True for embedded editor jobs
    
    # File information
    input_file_size_mb = Column(DECIMAL(8, 2))
    output_file_size_mb = Column(DECIMAL(8, 2))
    output_url = Column(String(1000))  # URL to download the processed video
    video_duration_seconds = Column(Integer)
    video_resolution = Column(String(20))
    
    # Processing times
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_duration_seconds = Column(Integer)
    
    # Error handling
    error_message = Column(Text)
    error_code = Column(String(50))
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Metadata and audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    job_metadata = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="video_jobs")
    files = relationship("File", back_populates="job", cascade="all, delete-orphan")
    status_history = relationship("JobStatusHistory", back_populates="job", cascade="all, delete-orphan")
    
    def update_status(self, new_status: JobStatus, message: str = None, progress: int = None):
        """Update job status with history tracking"""
        old_status = self.status
        self.status = new_status.value
        
        if message:
            self.progress_message = message
        
        if progress is not None:
            self.progress_percentage = min(100, max(0, progress))
        
        # Set timestamps based on status
        if new_status == JobStatus.PROCESSING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED]:
            if not self.completed_at:
                self.completed_at = datetime.utcnow()
            if self.started_at:
                duration = (self.completed_at - self.started_at).total_seconds()
                self.processing_duration_seconds = int(duration)
        
        return old_status
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return (self.status == JobStatus.FAILED.value and 
                self.retry_count < self.max_retries)
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
    
    @property
    def is_processing(self) -> bool:
        """Check if job is currently processing"""
        return self.status in [JobStatus.QUEUED.value, JobStatus.UPLOADING.value, JobStatus.PROCESSING.value]
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed successfully"""
        return self.status == JobStatus.COMPLETED.value
    
    @property
    def is_failed(self) -> bool:
        """Check if job has failed"""
        return self.status == JobStatus.FAILED.value
    
    @property
    def processing_time_minutes(self) -> float:
        """Get processing time in minutes"""
        if self.processing_duration_seconds:
            return self.processing_duration_seconds / 60.0
        return 0.0
    
    def get_input_file(self):
        """Get the input video file"""
        return next((f for f in self.files if f.file_type == "input_video"), None)
    
    def get_output_file(self):
        """Get the output video file"""
        return next((f for f in self.files if f.file_type == "output_video"), None)
    
    def estimate_credits_required(self) -> int:
        """Estimate credits required based on video duration"""
        if not self.video_duration_seconds:
            return 10  # Default estimate
        
        # Base calculation: 10 credits per minute
        minutes = self.video_duration_seconds / 60.0
        base_credits = int(minutes * 10)
        
        # Apply multipliers based on configuration
        config = self.processing_config or {}
        
        # High quality processing costs more
        if config.get('high_quality', False):
            base_credits = int(base_credits * 1.5)
        
        # Multiple language detection costs more
        if config.get('detect_multiple_languages', False):
            base_credits = int(base_credits * 1.3)
        
        return max(1, base_credits)  # Minimum 1 credit

class JobStatusHistory(Base):
    __tablename__ = "job_status_history"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String(20))
    new_status = Column(String(20), nullable=False)
    progress_percentage = Column(Integer)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status_metadata = Column(JSONB, default=dict)
    
    # Relationships
    job = relationship("VideoJob", back_populates="status_history")

class ProcessingTemplate(Base):
    __tablename__ = "processing_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    config = Column(JSONB, nullable=False)
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Common processing configurations
    @classmethod
    def get_default_configs(cls):
        return {
            "basic": {
                "name": "Basic Text Removal",
                "description": "Standard text inpainting for subtitles and overlays",
                "config": {
                    "font": "Arial.ttf",
                    "detect_multiple_languages": False,
                    "high_quality": False,
                    "remove_watermarks": True,
                    "processing_model": "advanced_lite"
                }
            },
            "high_quality": {
                "name": "High Quality Processing",
                "description": "Premium processing with better results",
                "config": {
                    "font": "Arial.ttf",
                    "detect_multiple_languages": True,
                    "high_quality": True,
                    "remove_watermarks": True,
                    "processing_model": "advanced_pro"
                }
            },
            "multi_language": {
                "name": "Multi-Language Detection",
                "description": "Detect and remove text in multiple languages",
                "config": {
                    "font": "Arial.ttf",
                    "detect_multiple_languages": True,
                    "high_quality": False,
                    "remove_watermarks": True,
                    "processing_model": "advanced_lite",
                    "languages": ["en", "es", "fr", "de", "zh", "ja"]
                }
            }
        }

# Import to ensure User model is available
from .user import User