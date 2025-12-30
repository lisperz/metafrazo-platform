"""
Embedded editor API endpoints for phraze.so integration
"""

import uuid
import logging
import datetime

from fastapi import APIRouter, Request, Query, Body, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.database import SessionLocal
from backend.models.job import VideoJob, JobStatus
from backend.auth.phraze import (
    PhrazeValidator,
    PhrazeCallbackService,
    CallbackStatus,
    ValidationResponse,
    ProcessRequest,
    ErrorResponse,
)
from backend.api.routes.embedded.processing import (
    send_started_callback,
    process_embedded_video,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/validate", response_model=ValidationResponse)
async def validate_access(
    request: Request,
    token: str = Query(..., description="JWT token from phraze.so")
):
    """
    Validate access from phraze.so redirect.
    Called when user lands on editor.phraze.so.
    Includes saved segments_data and effects_data for re-editing support.
    """
    try:
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        logger.info(
            f"Access validated for user {token_payload.user_id}, "
            f"job {token_payload.job_id}, tier {token_payload.subscription_tier}"
        )

        return ValidationResponse(
            valid=True,
            user_id=token_payload.user_id,
            job_id=token_payload.job_id,
            video_url=token_payload.video_url,
            callback_url=token_payload.callback_url,
            subscription_tier=token_payload.subscription_tier,
            is_pro_user=token_payload.is_pro_user,
            message="Access granted"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Validation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message=f"An error occurred during validation: {str(e)}",
                redirect_url=f"https://{settings.phraze_domain}"
            ).model_dump()
        )


@router.post("/process")
async def process_video(
    request: Request,
    background_tasks: BackgroundTasks,
    token: str = Query(..., description="JWT token from phraze.so"),
    processing_config: ProcessRequest = Body(default=ProcessRequest())
):
    """
    Process video from phraze.so.
    NO credit checking - phraze.so handles billing.
    """
    db = SessionLocal()
    try:
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        logger.info(
            f"Processing request for user {token_payload.user_id}, "
            f"job {token_payload.job_id}, type: {processing_config.processing_type}"
        )

        # Create internal job record for tracking
        internal_job_id = uuid.uuid4()
        # Use default user ID for embedded jobs from phraze.so
        default_user_id = uuid.UUID("03139de3-8cc6-4702-a2fd-048dff642ccb")
        job = VideoJob(
            id=internal_job_id,
            user_id=default_user_id,
            original_filename=f"phraze_job_{token_payload.job_id}",
            display_name=f"Phraze Edit - {token_payload.job_id[:8]}",
            status=JobStatus.QUEUED.value,
            is_embedded_job=True,
            processing_config={
                "phraze_user_id": token_payload.user_id,
                "phraze_job_id": token_payload.job_id,
                "video_url": token_payload.video_url,
                "callback_url": token_payload.callback_url,
                "processing_type": processing_config.processing_type,
                "target_language": processing_config.target_language,
                "audio_url": processing_config.audio_url,
                "segments": processing_config.segments,
            },
            job_metadata={
                "source": "phraze.so",
                "embedded_mode": True,
            },
            queued_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(job)
        db.commit()

        logger.info(
            f"Created embedded job {internal_job_id} for phraze job {token_payload.job_id}"
        )

        # Send "started" callback to phraze.so with segments/effects for re-editing
        background_tasks.add_task(
            send_started_callback,
            token_payload.callback_url,
            token_payload.job_id,
            str(internal_job_id),
            processing_config.segments,  # Include segments for re-editing
            processing_config.effects,   # Include effects for re-editing
        )

        # Start processing in background
        background_tasks.add_task(
            process_embedded_video,
            str(internal_job_id),
            token_payload,
            processing_config
        )

        return {
            "job_id": str(internal_job_id),
            "phraze_job_id": token_payload.job_id,
            "status": "processing",
            "message": "Video processing started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="PROCESSING_ERROR",
                message="Failed to start video processing",
                redirect_url=f"https://{settings.phraze_domain}"
            ).model_dump()
        )
    finally:
        db.close()


@router.get("/status/{job_id}")
async def get_job_status(
    request: Request,
    job_id: str,
    token: str = Query(..., description="JWT token from phraze.so")
):
    """
    Get status of an embedded video processing job.
    """
    db = SessionLocal()
    try:
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="JOB_NOT_FOUND",
                    message="Job not found",
                    job_id=job_id
                ).model_dump()
            )

        # Verify this job belongs to the phraze user/job
        config = job.processing_config or {}
        if config.get("phraze_job_id") != token_payload.job_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code="ACCESS_DENIED",
                    message="Access denied to this job",
                    job_id=job_id
                ).model_dump()
            )

        return {
            "job_id": str(job.id),
            "phraze_job_id": config.get("phraze_job_id"),
            "status": job.status,
            "progress": job.progress_percentage,
            "message": job.progress_message,
            "output_url": job.output_url,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )
    finally:
        db.close()


@router.post("/cancel/{job_id}")
async def cancel_job(
    request: Request,
    job_id: str,
    token: str = Query(..., description="JWT token from phraze.so")
):
    """
    Cancel an embedded video processing job.
    """
    db = SessionLocal()
    try:
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Verify ownership
        config = job.processing_config or {}
        if config.get("phraze_job_id") != token_payload.job_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Only cancel if not already completed/failed
        terminal_states = [
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELED.value
        ]
        if job.status in terminal_states:
            return {
                "job_id": str(job.id),
                "status": job.status,
                "message": "Job already in terminal state"
            }

        # Cancel the job
        job.status = JobStatus.CANCELED.value
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        job.progress_message = "Cancelled by user"
        db.commit()

        # Send callback
        await PhrazeCallbackService.send_callback(
            callback_url=config.get("callback_url", settings.phraze_callback_url),
            job_id=config.get("phraze_job_id"),
            status=CallbackStatus.FAILED,
            error_code="USER_CANCELLED",
            error_message="Job cancelled by user"
        )

        return {
            "job_id": str(job.id),
            "status": "canceled",
            "message": "Job cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )
    finally:
        db.close()
