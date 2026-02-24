"""
Video processing job routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import os
import magic
import logging

logger = logging.getLogger(__name__)

from backend.models.database import get_database
from backend.models.user import User
from backend.models.job import VideoJob, JobStatus, ProcessingTemplate
from backend.models.file import File as FileModel, FileType
from backend.auth.dependencies import get_current_user, validate_user_limits
from backend.config import settings

router = APIRouter()

# Pydantic models
class JobCreate(BaseModel):
    display_name: Optional[str] = None
    processing_config: Optional[dict] = None

class JobResponse(BaseModel):
    id: str
    user_id: str
    original_filename: str
    display_name: Optional[str]
    status: str
    progress_percentage: int
    progress_message: Optional[str]
    processing_config: dict
    estimated_credits: Optional[int]
    actual_credits_used: Optional[int]
    output_url: Optional[str]  # URL to download the processed video
    video_duration_seconds: Optional[int]
    video_resolution: Optional[str]
    queued_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    is_pro_job: Optional[bool] = False
    segments_data: Optional[dict] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    credits_used: Optional[int] = None
    progress: Optional[int] = None

    class Config:
        from_attributes = True

class JobStatusResponse(BaseModel):
    id: str
    status: str
    progress_percentage: int
    progress_message: Optional[str]
    error_message: Optional[str]
    download_url: Optional[str]
    
    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int

@router.post("/submit", response_model=JobResponse)
async def submit_video_job(
    video_file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
    processing_config: Optional[str] = Form("{}"),  # JSON string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Submit a new video processing job with S3 upload and automatic text inpainting
    """
    import json
    import os
    import shutil
    import uuid
    from backend.models.user import User
    from backend.workers.ghostcut_tasks import process_ghostcut_video
    
    # Use authenticated user from JWT token
    logger.info(f"🔐 Submitting job for user: {current_user.email} (ID: {current_user.id})")
    
    # Parse processing config
    try:
        config = json.loads(processing_config or "{}")
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid processing configuration JSON"
        )
    
    # Validate file
    if not video_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file extension
    file_ext = os.path.splitext(video_file.filename)[1].lower()
    if file_ext not in settings.allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {settings.allowed_video_extensions}"
        )
    
    # Check file size
    if video_file.size and video_file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Validate file content (MIME type)
    file_content = await video_file.read(1024)  # Read first 1KB for type detection
    await video_file.seek(0)  # Reset file pointer
    
    try:
        mime_type = magic.from_buffer(file_content, mime=True)
        if not mime_type.startswith('video/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a valid video format"
            )
    except Exception:
        # Fallback if python-magic is not available
        pass
    
    # Create job record
    job = VideoJob(
        user_id=current_user.id,
        original_filename=video_file.filename,
        display_name=display_name or video_file.filename,
        processing_config=config,
        input_file_size_mb=round(video_file.size / (1024 * 1024), 2) if video_file.size else None
    )
    
    # Set default processing config for automatic text inpainting
    if not config:
        config = {
            "type": "ghostcut_auto",
            "language": "auto",
            "erasures": [],
            "protected_areas": [],
            "text_areas": [],
            "auto_detect_text": True
        }
        job.processing_config = config
    
    db.add(job)
    db.flush()  # Get the job ID
    
    # Create file record for input video
    input_file = FileModel.create_for_upload(
        user_id=current_user.id,
        original_filename=video_file.filename,
        file_type=FileType.INPUT_VIDEO,
        job_id=job.id
    )
    input_file.file_size_bytes = video_file.size
    input_file.mime_type = mime_type if 'mime_type' in locals() else f"video/{file_ext[1:]}"
    
    db.add(input_file)
    db.commit()
    db.refresh(job)
    
    # TODO: Save uploaded file to storage
    # - Save to temporary location
    # - Upload to S3
    # - Queue job for processing
    
    # Save file to local storage and start S3 + Zhaoli processing
    try:
        # Save file to local storage first
        upload_dir = os.path.join(settings.upload_path, str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = uuid.uuid4()
        file_extension = os.path.splitext(video_file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        # Update processing config with local file path for S3 upload
        job.processing_config.update({
            "local_video_path": file_path,
            "video_file_id": str(file_id)
        })
        
        # Set estimated credits
        job.estimated_credits = 10  # Simple estimation
        
        # Set job status to queued
        from backend.models.job import JobStatus
        job.status = JobStatus.QUEUED.value  # Use .value to get the string
        job.progress_message = "Job queued for S3 upload and text inpainting"
        
        db.commit()
        
        # Direct processing without Celery (temporary solution)
        logger.info(f"Job {job.id} created successfully - Starting direct processing")
        
        # Import S3 service and Zhaoli client
        try:
            from backend.services.s3_service import s3_service
            from backend.services.ghostcut_client import GhostCutClient
            
            # Update job status
            job.status = JobStatus.PROCESSING.value
            job.progress_message = "Uploading video to S3..."
            job.progress_percentage = 10
            db.commit()
            
            # Upload to S3
            s3_key = f"users/{current_user.id}/jobs/{job.id}/{os.path.basename(file_path)}"
            video_url = s3_service.upload_video_and_get_url(file_path, s3_key)
            
            if not video_url:
                raise Exception("Failed to upload video to S3")
            
            logger.info(f"Video uploaded to S3: {video_url}")
            job.progress_message = "Video uploaded to S3, calling Zhaoli API..."
            job.progress_percentage = 30
            db.commit()
            
            # Call Zhaoli API with credentials from config
            import json as json_module
            zhaoli_config_path = '/app/zhaoli_config.json'
            try:
                with open(zhaoli_config_path, 'r') as f:
                    zhaoli_config = json_module.load(f)
            except:
                # Fallback to hardcoded credentials if file not found
                zhaoli_config = {
                    "app_key": "fb518b019d3341e2a3a32e730d0797c9",
                    "app_secret": "fcbc542efcb44a198dd53c451503fd04",
                    "ghostcut_uid": "b48052d4449f46a3b4654473c41a2a6a"
                }
            
            ghostcut = GhostCutClient(
                api_key=zhaoli_config['app_key'],
                api_secret=zhaoli_config['app_secret']
            )
            # Call submit_job directly with proper parameters
            result = ghostcut.submit_job(
                video_url=video_url,
                ghostcut_uid=zhaoli_config['ghostcut_uid'],
                language="auto",
                erasures=[],
                protected_areas=[],
                text_areas=[],
                auto_detect_text=True
            )
            
            if result:
                job.processing_config['zhaoli_task_id'] = result
                job.progress_message = f"Processing started with Zhaoli API (Task ID: {result})"
                job.progress_percentage = 50
                logger.info(f"Zhaoli API task created: {result}")
            else:
                job.status = JobStatus.FAILED.value
                job.error_message = "Failed to start Zhaoli processing"
                logger.error(f"Failed to start Zhaoli processing for job {job.id}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {str(e)}")
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.progress_message = "Processing failed"
            db.commit()
        
    except Exception as e:
        # Still commit the job record even if processing failed
        # This way the user can see the failed job status
        try:
            db.commit()  # Save the job record
        except:
            db.rollback()
        
        # Clean up temporary file
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        # Don't raise exception, return the job with failed status
        logger.error(f"Failed to process upload: {str(e)}")
    
    # Filter out timeout messages - never show them to users
    error_message = job.error_message
    job_status = job.status
    if error_message and ('timeout' in error_message.lower() or 'timed out' in error_message.lower()):
        error_message = None  # Hide timeout errors completely
        # Keep job in processing state if it has timeout error
        if job_status == 'failed':
            job_status = 'processing'
    
    return JobResponse(
        id=str(job.id),
        user_id=str(job.user_id),
        original_filename=job.original_filename,
        display_name=job.display_name,
        status=job_status,
        progress_percentage=job.progress_percentage,
        progress_message=job.progress_message,
        processing_config=job.processing_config,
        estimated_credits=job.estimated_credits,
        actual_credits_used=job.actual_credits_used,
        output_url=job.output_url,
        video_duration_seconds=job.video_duration_seconds,
        video_resolution=job.video_resolution,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=error_message,
        created_at=job.created_at
    )

@router.get("/", response_model=JobListResponse)
async def get_user_jobs(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Get user's video processing jobs
    """
    # Use authenticated user from JWT token
    logger.info(f"🔐 Getting jobs for user: {current_user.email} (ID: {current_user.id})")
    
    # Build query
    query = db.query(VideoJob).filter(VideoJob.user_id == current_user.id)
    
    # Apply status filter
    if status_filter:
        query = query.filter(VideoJob.status == status_filter)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(VideoJob.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Convert to response format
    job_responses = []
    for job in jobs:
        # Filter out timeout messages - never show them to users
        error_message = job.error_message
        status = job.status
        if error_message and ('timeout' in error_message.lower() or 'timed out' in error_message.lower()):
            error_message = None  # Hide timeout errors completely
            # Keep job in processing state if it has timeout error
            if status == 'failed':
                status = 'processing'
        
        job_responses.append(JobResponse(
            id=str(job.id),
            user_id=str(job.user_id),
            original_filename=job.original_filename,
            display_name=job.display_name,
            status=status,
            progress_percentage=job.progress_percentage,
            progress_message=job.progress_message,
            processing_config=job.processing_config,
            estimated_credits=job.estimated_credits,
            actual_credits_used=job.actual_credits_used,
            output_url=job.output_url,
            video_duration_seconds=job.video_duration_seconds,
            video_resolution=job.video_resolution,
            queued_at=job.queued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=error_message,
            created_at=job.created_at,
            is_pro_job=getattr(job, 'is_pro_job', False),
            segments_data=getattr(job, 'segments_data', None),
            file_size=getattr(job, 'input_file_size_mb', None),
            duration=job.video_duration_seconds,
            credits_used=job.actual_credits_used,
            progress=job.progress_percentage
        ))
    
    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_details(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Get details of a specific job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    # Use authenticated user to ensure only owner can access job
    job = db.query(VideoJob).filter(
        VideoJob.id == job_uuid,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Filter out timeout messages - never show them to users
    error_message = job.error_message
    job_status = job.status
    if error_message and ('timeout' in error_message.lower() or 'timed out' in error_message.lower()):
        error_message = None  # Hide timeout errors completely
        # Keep job in processing state if it has timeout error
        if job_status == 'failed':
            job_status = 'processing'
    
    return JobResponse(
        id=str(job.id),
        user_id=str(job.user_id),
        original_filename=job.original_filename,
        display_name=job.display_name,
        status=job_status,
        progress_percentage=job.progress_percentage,
        progress_message=job.progress_message,
        processing_config=job.processing_config,
        estimated_credits=job.estimated_credits,
        actual_credits_used=job.actual_credits_used,
        output_url=job.output_url,
        video_duration_seconds=job.video_duration_seconds,
        video_resolution=job.video_resolution,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=error_message,
        created_at=job.created_at
    )

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Get current status of a job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = db.query(VideoJob).filter(
        VideoJob.id == job_uuid,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Get download URL if job is completed
    download_url = None
    if job.is_completed:
        output_file = job.get_output_file()
        if output_file:
            download_url = f"/api/v1/files/{output_file.id}/download"
    
    return JobStatusResponse(
        id=str(job.id),
        status=job.status,
        progress_percentage=job.progress_percentage,
        progress_message=job.progress_message,
        error_message=job.error_message,
        download_url=download_url
    )

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Cancel a processing job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = db.query(VideoJob).filter(
        VideoJob.id == job_uuid,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if job can be cancelled
    if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    # Cancel job
    job.update_status(JobStatus.CANCELED, "Job cancelled by user")
    db.commit()
    
    # TODO: Cancel background processing task
    # cancel_processing_task(job.id)
    
    return {"message": "Job cancelled successfully"}

@router.post("/{job_id}/check-zhaoli-status")
async def check_zhaoli_status(
    job_id: str,
    db: Session = Depends(get_database)
):
    """
    Check Zhaoli API status for a job and update accordingly
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = db.query(VideoJob).filter(VideoJob.id == job_uuid).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if job has Zhaoli task ID
    zhaoli_task_id = job.processing_config.get('zhaoli_task_id') if job.processing_config else None
    if not zhaoli_task_id:
        return {"status": job.status, "message": "No Zhaoli task ID found"}
    
    try:
        # Import Zhaoli client
        from backend.services.ghostcut_client import GhostCutClient
        
        # Initialize with credentials
        zhaoli_config = {
            "app_key": "fb518b019d3341e2a3a32e730d0797c9",
            "app_secret": "fcbc542efcb44a198dd53c451503fd04"
        }
        
        ghostcut = GhostCutClient(
            api_key=zhaoli_config['app_key'],
            api_secret=zhaoli_config['app_secret'],
            api_url="https://api.zhaoli.com"
        )
        
        # Check status
        result = ghostcut.get_job_status(str(zhaoli_task_id))
        
        # Update job based on status
        if result['status'] == 'completed':
            job.status = JobStatus.COMPLETED.value
            job.progress_percentage = 100
            job.progress_message = "Processing completed"
            job.completed_at = datetime.utcnow()
            
            # Store output URL
            if result.get('output_url'):
                if not job.processing_config:
                    job.processing_config = {}
                job.processing_config['output_url'] = result['output_url']
                
        elif result['status'] == 'processing':
            job.status = JobStatus.PROCESSING.value
            job.progress_percentage = result.get('progress', 50)
            job.progress_message = result.get('message', 'Processing...')
            
        elif result['status'] == 'error' or result['status'] == 'failed':
            job.status = JobStatus.FAILED.value
            job.error_message = result.get('error', 'Processing failed')
            job.progress_message = "Processing failed"
        
        db.commit()
        
        return {
            "status": job.status,
            "progress": job.progress_percentage,
            "message": job.progress_message,
            "output_url": job.processing_config.get('output_url') if job.processing_config else None
        }
        
    except Exception as e:
        logger.error(f"Error checking Zhaoli status: {str(e)}")
        return {"status": job.status, "error": str(e)}

@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Retry a failed job
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = db.query(VideoJob).filter(
        VideoJob.id == job_uuid,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if job can be retried
    if not job.can_retry():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be retried (not failed or max retries reached)"
        )
    
    # Check if user has sufficient credits
    if not current_user.has_sufficient_credits(job.estimated_credits or 10):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits for retry. Required: {job.estimated_credits}, Available: {current_user.credits_balance}"
        )
    
    # Reset job for retry
    job.increment_retry()
    job.update_status(JobStatus.QUEUED, f"Job queued for retry (attempt {job.retry_count + 1})")
    job.error_message = None
    job.error_code = None
    job.progress_percentage = 0
    
    db.commit()
    
    # TODO: Queue job for background processing
    # queue_video_processing_job(job.id)
    
    return {"message": "Job queued for retry"}

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Delete a job and its associated files
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    job = db.query(VideoJob).filter(
        VideoJob.id == job_uuid,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Cancel job if it's still processing
    if job.is_processing:
        job.update_status(JobStatus.CANCELED, "Job cancelled for deletion")
        # TODO: Cancel background processing task
        # cancel_processing_task(job.id)
    
    # Delete associated files
    for file in job.files:
        # TODO: Delete file from storage
        # delete_file_from_storage(file.storage_path)
        db.delete(file)
    
    # Delete job
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}

@router.get("/templates/", response_model=List[dict])
async def get_processing_templates():
    """
    Get available processing templates
    """
    templates = ProcessingTemplate.get_default_configs()
    return [
        {
            "id": key,
            "name": config["name"],
            "description": config["description"],
            "config": config["config"]
        }
        for key, config in templates.items()
    ]