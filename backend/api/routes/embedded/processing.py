"""
Embedded video processing functions for phraze.so integration
Handles actual processing logic separated from route handlers
"""

import uuid
import logging
import datetime
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.models.database import SessionLocal
from backend.models.job import VideoJob, JobStatus
from backend.auth.phraze import (
    PhrazeTokenPayload,
    PhrazeCallbackService,
    ProcessRequest,
)
from backend.services.embedded_processing import embedded_processing_service
from backend.config import settings

logger = logging.getLogger(__name__)


async def send_started_callback(
    callback_url: str,
    phraze_job_id: str,
    internal_job_id: str,
    segments_data: Optional[list] = None,
    effects_data: Optional[list] = None
):
    """Send started callback to phraze.so with segments/effects for re-editing"""
    metadata = {"internal_job_id": internal_job_id}

    # Include segments and effects data so Phraze.so can save them for re-editing
    if segments_data:
        metadata["segments_data"] = segments_data
    if effects_data:
        metadata["effects_data"] = effects_data

    await PhrazeCallbackService.notify_job_started(
        callback_url=callback_url,
        job_id=phraze_job_id,
        metadata=metadata
    )


async def start_real_lipsync_processing(
    job: VideoJob,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest,
    db: Session
) -> None:
    """
    Start real Sync.so lip-sync processing

    This creates a Sync.so generation and stores the generation_id.
    Celery beat will poll for completion and send callback when done.
    """
    try:
        segments = processing_config.segments or []

        # Build audio URL mapping from segments
        # In embedded mode, audio URLs should be provided in the segments
        audio_url_mapping = {}
        for seg in segments:
            audio_input = seg.get("audioInput", {})
            ref_id = audio_input.get("refId")
            audio_url = audio_input.get("url")
            if ref_id and audio_url:
                audio_url_mapping[ref_id] = audio_url

        logger.info(
            f"Job {job.id}: Starting real Sync.so processing with "
            f"{len(segments)} segments, {len(audio_url_mapping)} audio files"
        )

        # Create Sync.so generation
        if len(segments) > 0 and len(audio_url_mapping) > 0:
            generation_id = await embedded_processing_service.create_lipsync_generation(
                video_url=token_payload.video_url,
                segments=segments,
                audio_url_mapping=audio_url_mapping
            )
        elif processing_config.audio_url:
            # Simple single-audio lip-sync
            generation_id = await embedded_processing_service.create_simple_lipsync(
                video_url=token_payload.video_url,
                audio_url=processing_config.audio_url
            )
        else:
            raise ValueError("No audio source provided for lip-sync")

        # Update job with Sync.so generation ID
        job.status = JobStatus.PROCESSING.value
        job.is_pro_job = True  # Mark as Pro job for Celery polling
        job.is_embedded_job = True
        job.zhaoli_task_id = generation_id  # Store generation ID for polling
        job.progress_percentage = 30
        job.progress_message = "Lip-sync generation started on Sync.so..."

        # Store phraze callback info in job_metadata
        if not job.job_metadata:
            job.job_metadata = {}
        job.job_metadata["sync_generation_id"] = generation_id
        job.job_metadata["phraze_callback_url"] = token_payload.callback_url
        job.job_metadata["phraze_job_id"] = token_payload.job_id
        job.job_metadata["phraze_user_id"] = token_payload.user_id
        flag_modified(job, 'job_metadata')

        db.commit()

        logger.info(
            f"Job {job.id}: Sync.so generation {generation_id} created. "
            "Celery will poll for completion."
        )

    except Exception as e:
        logger.error(f"Job {job.id}: Failed to start Sync.so processing: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        raise


async def process_embedded_video(
    internal_job_id: str,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest
):
    """
    Background task to start embedded video processing.
    For lip-sync, this creates a Sync.so job and returns immediately.
    Celery beat handles polling and completion callback.
    """
    db = SessionLocal()
    start_time = datetime.datetime.now(datetime.timezone.utc)

    try:
        job = db.query(VideoJob).filter(
            VideoJob.id == uuid.UUID(internal_job_id)
        ).first()
        if not job:
            logger.error(f"Job {internal_job_id} not found")
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING.value
        job.started_at = start_time
        job.progress_percentage = 10
        job.progress_message = "Starting video processing..."
        db.commit()

        processing_type = processing_config.processing_type

        if processing_type == "text_removal":
            await process_text_removal(job, token_payload, db)
        elif processing_type == "lip_sync":
            # Start real Sync.so processing (non-blocking)
            await start_real_lipsync_processing(
                job, token_payload, processing_config, db
            )
            # Don't send callback here - Celery will handle it when done
            return
        elif processing_type == "both":
            # Start combined processing (non-blocking) - Celery handles polling
            await start_combined_lipsync_and_text_removal(
                job, token_payload, processing_config, db
            )
            # Don't send callback here - Celery will handle it when done
            return
        else:
            raise ValueError(f"Unknown processing type: {processing_type}")

        # For non-lip-sync jobs, send completion callback here
        end_time = datetime.datetime.now(datetime.timezone.utc)
        processing_time = int((end_time - start_time).total_seconds())

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

        job = db.query(VideoJob).filter(
            VideoJob.id == uuid.UUID(internal_job_id)
        ).first()
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()

        end_time = datetime.datetime.now(datetime.timezone.utc)
        processing_time = int((end_time - start_time).total_seconds())

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


async def process_text_removal(
    job: VideoJob,
    token_payload: PhrazeTokenPayload,
    db: Session
):
    """Process text removal using GhostCut API"""
    from backend.api.routes.jobs.processing.direct_process_original import (
        call_ghostcut_api,
        check_ghostcut_status_async
    )

    job.progress_percentage = 20
    job.progress_message = "Submitting to text removal service..."
    db.commit()

    ghostcut_task_id = await call_ghostcut_api(
        token_payload.video_url, str(job.id), []
    )

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


async def start_combined_lipsync_and_text_removal(
    job: VideoJob,
    token_payload: PhrazeTokenPayload,
    processing_config: ProcessRequest,
    db: Session
) -> None:
    """
    Start combined lip-sync + text removal processing (non-blocking).

    This creates a Sync.so generation and stores the effects data.
    Celery beat will poll for lip-sync completion, then chain to text removal.

    Flow (handled by Celery):
    1. Lip-sync via Sync.so with segments
    2. Celery polls for Sync.so completion
    3. When lip-sync done, Celery starts text removal via GhostCut
    4. Celery polls for GhostCut completion
    5. Celery sends callback with final output
    """
    try:
        segments = processing_config.segments or []
        effects = processing_config.effects or []

        # Build audio URL mapping from segments
        audio_url_mapping = {}
        for seg in segments:
            audio_input = seg.get("audioInput", {})
            ref_id = audio_input.get("refId")
            audio_url = audio_input.get("url")
            if ref_id and audio_url:
                audio_url_mapping[ref_id] = audio_url

        has_segments = len(segments) > 0 and len(audio_url_mapping) > 0

        if not has_segments:
            raise ValueError(
                "Segments with audio are required for combined processing"
            )

        logger.info(
            f"Job {job.id}: Starting combined processing with "
            f"{len(segments)} segments, {len(effects)} effects"
        )

        # Create Sync.so generation
        generation_id = await embedded_processing_service.create_lipsync_generation(
            video_url=token_payload.video_url,
            segments=segments,
            audio_url_mapping=audio_url_mapping
        )

        # Update job - mark as embedded for Celery polling
        job.status = JobStatus.PROCESSING.value
        job.is_pro_job = True
        job.is_embedded_job = True
        job.zhaoli_task_id = generation_id
        job.progress_percentage = 20
        job.progress_message = "Lip-sync processing..."

        # Store all metadata for Celery to use
        if not job.job_metadata:
            job.job_metadata = {}
        job.job_metadata["sync_generation_id"] = generation_id
        job.job_metadata["phraze_callback_url"] = token_payload.callback_url
        job.job_metadata["phraze_job_id"] = token_payload.job_id
        job.job_metadata["phraze_user_id"] = token_payload.user_id
        # Store effects for text removal step (Celery will use this)
        job.job_metadata["pending_effects"] = effects
        job.job_metadata["processing_type"] = "both"
        flag_modified(job, 'job_metadata')

        db.commit()

        logger.info(
            f"Job {job.id}: Sync.so generation {generation_id} created. "
            "Celery will poll and chain to text removal when done."
        )

    except Exception as e:
        logger.error(f"Job {job.id}: Failed to start combined processing: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        raise
