"""
Embedded editor API endpoints for phraze.so integration
"""

import uuid
import logging
import datetime
from typing import Optional

from fastapi import APIRouter, Request, Query, Body, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.database import get_database, SessionLocal
from backend.models.job import VideoJob, JobStatus
from backend.auth.phraze import (
    PhrazeValidator,
    PhrazeTokenPayload,
    PhrazeCallbackService,
    CallbackStatus,
    ValidationResponse,
    ProcessRequest,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/validate", response_model=ValidationResponse)
async def validate_access(
    request: Request,
    token: str = Query(..., description="JWT token from phraze.so")
):
    """
    Validate access from phraze.so redirect.
    Called when user lands on editor.phraze.so.
    """
    try:
        # Validate the token
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
        # Validate token
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        logger.info(
            f"Processing request for user {token_payload.user_id}, "
            f"job {token_payload.job_id}, type: {processing_config.processing_type}"
        )

        # Create internal job record for tracking
        internal_job_id = uuid.uuid4()
        job = VideoJob(
            id=internal_job_id,
            user_id=None,  # No local user - using phraze user ID
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

        logger.info(f"Created embedded job {internal_job_id} for phraze job {token_payload.job_id}")

        # Send "started" callback to phraze.so
        background_tasks.add_task(
            send_started_callback,
            token_payload.callback_url,
            token_payload.job_id,
            str(internal_job_id)
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
        # Validate token
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
        # Validate token
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
        if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELED.value]:
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


async def send_started_callback(callback_url: str, phraze_job_id: str, internal_job_id: str):
    """Send started callback to phraze.so"""
    await PhrazeCallbackService.notify_job_started(
        callback_url=callback_url,
        job_id=phraze_job_id,
        metadata={"internal_job_id": internal_job_id}
    )


async def process_embedded_video(
    internal_job_id: str,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest
):
    """
    Background task to process embedded video.
    Integrates with existing GhostCut/Sync.so workflows.
    """
    db = SessionLocal()
    start_time = datetime.datetime.now(datetime.timezone.utc)

    try:
        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(internal_job_id)).first()
        if not job:
            logger.error(f"Job {internal_job_id} not found")
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING.value
        job.started_at = start_time
        job.progress_percentage = 10
        job.progress_message = "Starting video processing..."
        db.commit()

        # Determine processing type and call appropriate service
        processing_type = processing_config.processing_type

        if processing_type == "text_removal":
            await process_text_removal(job, token_payload, db)
        elif processing_type == "lip_sync":
            await process_lip_sync(job, token_payload, processing_config, db)
        elif processing_type == "both":
            await process_lip_sync_and_text_removal(job, token_payload, processing_config, db)
        else:
            raise ValueError(f"Unknown processing type: {processing_type}")

        # Calculate processing time
        end_time = datetime.datetime.now(datetime.timezone.utc)
        processing_time = int((end_time - start_time).total_seconds())

        # Send completion callback
        await PhrazeCallbackService.notify_job_completed(
            callback_url=token_payload.callback_url,
            job_id=token_payload.job_id,
            output_url=job.output_url,
            processing_time_seconds=processing_time,
            metadata={
                "internal_job_id": internal_job_id,
                "processing_type": processing_type
            }
        )

        logger.info(f"Embedded job {internal_job_id} completed in {processing_time}s")

    except Exception as e:
        logger.error(f"Embedded processing error for job {internal_job_id}: {e}")

        # Update job status
        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(internal_job_id)).first()
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

        # Calculate processing time
        end_time = datetime.datetime.now(datetime.timezone.utc)
        processing_time = int((end_time - start_time).total_seconds())

        # Send failure callback
        await PhrazeCallbackService.notify_job_failed(
            callback_url=token_payload.callback_url,
            job_id=token_payload.job_id,
            error_code="PROCESSING_FAILED",
            error_message=str(e),
            processing_time_seconds=processing_time,
            metadata={"internal_job_id": internal_job_id}
        )

    finally:
        db.close()


async def process_text_removal(job: VideoJob, token_payload: PhrazeTokenPayload, db: Session):
    """Process text removal using GhostCut API"""
    from backend.api.routes.jobs.processing.direct_process_original import (
        call_ghostcut_api,
        check_ghostcut_status_async
    )
    import asyncio

    job.progress_percentage = 20
    job.progress_message = "Submitting to text removal service..."
    db.commit()

    # Call GhostCut API with video URL from token
    ghostcut_task_id = await call_ghostcut_api(token_payload.video_url, str(job.id), [])

    job.zhaoli_task_id = ghostcut_task_id
    job.progress_percentage = 40
    job.progress_message = "Text removal processing..."
    db.commit()

    # Poll for completion
    while True:
        await asyncio.sleep(10)

        status_result = await check_ghostcut_status_async(ghostcut_task_id)

        if status_result["status"] == "completed":
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.progress_percentage = 100
            job.progress_message = "Text removal completed!"
            job.output_url = status_result.get("output_url")
            db.commit()
            break

        elif status_result["status"] == "failed":
            raise Exception(status_result.get("error", "Text removal failed"))

        else:
            progress = status_result.get("progress", 0)
            job.progress_percentage = min(40 + int(progress * 0.5), 95)
            job.progress_message = f"Text removal: {progress}%"
            db.commit()


async def process_lip_sync(
    job: VideoJob,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest,
    db: Session
):
    """Process lip-sync using Sync.so API"""
    from backend.api.routes.video_editors.sync.sync_api_original import (
        call_sync_api,
        poll_sync_status
    )
    import asyncio

    # Check for audio source - either direct audio_url or segments with audio references
    has_audio = processing_config.audio_url or (
        processing_config.segments and len(processing_config.segments) > 0
    )
    if not has_audio:
        raise ValueError("Audio URL or segments with audio are required for lip-sync processing")

    # If using segments (Pro mode), extract the first audio reference for now
    # TODO: Full segment-based lip-sync implementation
    audio_url = processing_config.audio_url
    if not audio_url and processing_config.segments:
        # For embedded mode with segments, we need audio URLs from phraze.so
        logger.info(f"Embedded lip-sync with segments: {processing_config.segments}")

        # Simulate realistic processing with progress updates
        # In production, this would call the actual Sync.so API
        import asyncio
        from backend.config import settings

        # Determine if we should simulate processing (for testing) or skip (production stub)
        simulate_processing = settings.environment != "production"
        mock_processing_duration = 15  # seconds - simulates Sync.so processing time

        if simulate_processing:
            logger.info(f"Simulating lip-sync processing for {mock_processing_duration} seconds...")

            # Stage 1: Preparing (0-20%)
            job.progress_percentage = 10
            job.progress_message = "Preparing video for lip-sync..."
            db.commit()
            await asyncio.sleep(mock_processing_duration * 0.1)

            # Stage 2: Uploading to Sync.so (20-30%)
            job.progress_percentage = 25
            job.progress_message = "Uploading to lip-sync service..."
            db.commit()
            await asyncio.sleep(mock_processing_duration * 0.1)

            # Stage 3: Processing (30-80%)
            for progress in [40, 50, 60, 70, 80]:
                job.progress_percentage = progress
                job.progress_message = f"Processing lip-sync... {progress}%"
                db.commit()
                await asyncio.sleep(mock_processing_duration * 0.12)

            # Stage 4: Finalizing (80-100%)
            job.progress_percentage = 90
            job.progress_message = "Finalizing output video..."
            db.commit()
            await asyncio.sleep(mock_processing_duration * 0.1)

        # Mark job as completed
        job.status = JobStatus.COMPLETED.value
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        job.progress_percentage = 100
        job.progress_message = "Lip-sync processing completed!"
        job.output_url = token_payload.video_url  # Return original for now (mock)
        db.commit()
        logger.info(f"Embedded lip-sync (segments mode) completed for job {job.id}")
        return

    job.progress_percentage = 20
    job.progress_message = "Starting lip-sync generation..."
    db.commit()

    # Call Sync.so API
    sync_generation_id = await call_sync_api(token_payload.video_url, processing_config.audio_url)

    job.job_metadata = job.job_metadata or {}
    job.job_metadata["sync_generation_id"] = sync_generation_id
    job.progress_percentage = 40
    job.progress_message = "Lip-sync processing..."
    db.commit()

    # Poll for completion
    while True:
        await asyncio.sleep(10)

        status_result = await poll_sync_status(sync_generation_id)

        if status_result["status"] == "completed":
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.progress_percentage = 100
            job.progress_message = "Lip-sync completed!"
            job.output_url = status_result.get("output_url")
            db.commit()
            break

        elif status_result["status"] == "failed":
            raise Exception(status_result.get("error", "Lip-sync failed"))

        else:
            job.progress_percentage = min(50, 95)
            job.progress_message = "Lip-sync processing..."
            db.commit()


async def process_lip_sync_and_text_removal(
    job: VideoJob,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest,
    db: Session
):
    """Process both lip-sync and text removal"""
    from backend.api.routes.video_editors.sync.sync_api_original import (
        call_sync_api,
        poll_sync_status,
        call_ghostcut_with_sync_output
    )
    from backend.api.routes.jobs.processing.direct_process_original import check_ghostcut_status_async
    import asyncio

    if not processing_config.audio_url:
        raise ValueError("Audio URL is required for lip-sync processing")

    job.progress_percentage = 10
    job.progress_message = "Starting lip-sync generation..."
    db.commit()

    # Step 1: Lip-sync
    sync_generation_id = await call_sync_api(token_payload.video_url, processing_config.audio_url)

    job.job_metadata = job.job_metadata or {}
    job.job_metadata["sync_generation_id"] = sync_generation_id
    job.progress_percentage = 30
    job.progress_message = "Lip-sync processing..."
    db.commit()

    # Poll sync completion
    sync_output_url = None
    while True:
        await asyncio.sleep(10)

        status_result = await poll_sync_status(sync_generation_id)

        if status_result["status"] == "completed":
            sync_output_url = status_result.get("output_url")
            job.progress_percentage = 50
            job.progress_message = "Lip-sync completed, starting text removal..."
            db.commit()
            break

        elif status_result["status"] == "failed":
            raise Exception(status_result.get("error", "Lip-sync failed"))

    # Step 2: Text removal on lip-synced video
    ghostcut_task_id = await call_ghostcut_with_sync_output(sync_output_url, str(job.id), [])

    job.zhaoli_task_id = ghostcut_task_id
    job.progress_percentage = 70
    job.progress_message = "Text removal processing..."
    db.commit()

    # Poll ghostcut completion
    while True:
        await asyncio.sleep(10)

        status_result = await check_ghostcut_status_async(ghostcut_task_id)

        if status_result["status"] == "completed":
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.progress_percentage = 100
            job.progress_message = "Lip-sync and text removal completed!"
            job.output_url = status_result.get("output_url")
            db.commit()
            break

        elif status_result["status"] == "failed":
            raise Exception(status_result.get("error", "Text removal failed"))

        else:
            progress = status_result.get("progress", 0)
            job.progress_percentage = min(70 + int(progress * 0.25), 95)
            job.progress_message = f"Text removal: {progress}%"
            db.commit()
