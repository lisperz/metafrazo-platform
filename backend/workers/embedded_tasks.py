"""
Celery tasks for embedded video processing (phraze.so integration)
Handles Sync.so polling, GhostCut chaining, and phraze.so callback sending
"""

import logging
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.orm.attributes import flag_modified

from backend.workers.celery_app import app
from backend.models.job import VideoJob, JobStatus
from backend.workers.video_tasks.helpers import get_db
from backend.services.embedded_processing import embedded_processing_service
from backend.auth.phraze import PhrazeCallbackService

logger = logging.getLogger(__name__)


async def check_embedded_job(job: VideoJob) -> None:
    """
    Check status of an embedded job and send callback if completed/failed.
    Handles both Sync.so (lip-sync) and GhostCut (text removal) phases.
    """
    try:
        task_id = job.zhaoli_task_id
        if not task_id:
            logger.warning(f"Embedded job {job.id}: No task ID found")
            return

        metadata = job.job_metadata or {}
        callback_url = metadata.get("phraze_callback_url")
        phraze_job_id = metadata.get("phraze_job_id")
        phraze_user_id = metadata.get("phraze_user_id")
        current_phase = metadata.get("current_phase", "sync")  # sync or ghostcut

        if not callback_url or not phraze_job_id:
            logger.warning(f"Embedded job {job.id}: Missing callback info")
            return

        logger.info(
            f"Checking embedded job {job.id}: phase={current_phase}, task={task_id}"
        )

        if current_phase == "ghostcut":
            # Check GhostCut status for text removal phase
            await check_ghostcut_phase(
                job, task_id, callback_url, phraze_job_id
            )
        else:
            # Check Sync.so status for lip-sync phase
            await check_sync_phase(
                job, task_id, callback_url, phraze_job_id, phraze_user_id
            )

    except Exception as e:
        logger.error(f"Error checking embedded job {job.id}: {e}", exc_info=True)


async def check_sync_phase(
    job: VideoJob,
    generation_id: str,
    callback_url: str,
    phraze_job_id: str,
    phraze_user_id: str
) -> None:
    """
    Check Sync.so generation status for lip-sync phase.
    """
    status_result = await embedded_processing_service.check_generation_status(
        generation_id
    )

    status = status_result.get("status")
    logger.info(f"Embedded job {job.id}: Sync.so status = {status}")

    if status == "COMPLETED":
        await handle_embedded_completion(
            job, status_result, callback_url, phraze_job_id, phraze_user_id
        )
    elif status in ["REJECTED", "FAILED"]:
        await handle_embedded_failure(
            job, status_result, callback_url, phraze_job_id
        )
    elif status == "PROCESSING":
        # Update progress
        job.progress_percentage = min(job.progress_percentage + 5, 55)
        job.progress_message = "Lip-sync processing..."


async def check_ghostcut_phase(
    job: VideoJob,
    ghostcut_task_id: str,
    callback_url: str,
    phraze_job_id: str
) -> None:
    """
    Check GhostCut status for text removal phase.
    Downloads output and uploads to S3 before finalizing.
    """
    from backend.api.routes.jobs.processing.process_utils import (
        check_ghostcut_status_async
    )

    status_result = await check_ghostcut_status_async(ghostcut_task_id)
    status = status_result.get("status")
    logger.info(f"Embedded job {job.id}: GhostCut status = {status}")

    if status == "completed":
        output_url = status_result.get("output_url")
        if output_url:
            # GhostCut completed - download and upload to S3 before finalizing
            logger.info(f"Embedded job {job.id}: Downloading GhostCut result...")
            try:
                metadata = job.job_metadata or {}
                phraze_user_id = metadata.get("phraze_user_id", "unknown")

                # Download from GhostCut CDN and upload to our S3
                s3_url = await embedded_processing_service.download_and_upload_result(
                    output_url=output_url,
                    user_id=phraze_user_id,
                    job_id=str(job.id)
                )
                logger.info(f"Embedded job {job.id}: GhostCut output uploaded to S3")

                await finalize_embedded_job(
                    job, s3_url, callback_url, phraze_job_id
                )
            except Exception as e:
                logger.error(
                    f"Embedded job {job.id}: Failed to upload GhostCut output to S3: {e}"
                )
                await handle_ghostcut_failure(
                    job, f"Failed to upload output: {str(e)}",
                    callback_url, phraze_job_id
                )
        else:
            logger.error(
                f"Embedded job {job.id}: GhostCut completed but no output URL"
            )
            await handle_ghostcut_failure(
                job, "No output URL from GhostCut",
                callback_url, phraze_job_id
            )

    elif status == "error":
        error_msg = status_result.get("error", "GhostCut processing failed")
        await handle_ghostcut_failure(
            job, error_msg, callback_url, phraze_job_id
        )

    elif status in ["processing", "pending"]:
        progress = status_result.get("progress", 0)
        # Map GhostCut progress (0-100) to our range (60-95)
        job.progress_percentage = min(60 + int(progress * 0.35), 95)
        job.progress_message = f"Text removal: {progress}%"


async def handle_ghostcut_failure(
    job: VideoJob,
    error_msg: str,
    callback_url: str,
    phraze_job_id: str
) -> None:
    """
    Handle GhostCut failure. Fall back to lip-sync output if available.
    """
    metadata = job.job_metadata or {}
    lipsync_output = metadata.get("lipsync_output_url")

    if lipsync_output:
        # Fall back to lip-sync only result
        logger.warning(
            f"Embedded job {job.id}: GhostCut failed, falling back to lip-sync"
        )
        await finalize_embedded_job(
            job, lipsync_output, callback_url, phraze_job_id,
            fallback_message="Lip-sync completed (text removal failed)"
        )
    else:
        # No fallback available - mark as failed
        logger.error(
            f"Embedded job {job.id}: GhostCut failed with no fallback: {error_msg}"
        )
        job.status = JobStatus.FAILED.value
        job.error_message = error_msg
        job.completed_at = datetime.utcnow()

        await PhrazeCallbackService.notify_job_failed(
            callback_url=callback_url,
            job_id=phraze_job_id,
            error_code="GHOSTCUT_FAILED",
            error_message=error_msg,
            processing_time_seconds=0,
            metadata={"internal_job_id": str(job.id)}
        )


async def handle_embedded_completion(
    job: VideoJob,
    status_result: dict,
    callback_url: str,
    phraze_job_id: str,
    phraze_user_id: str
) -> None:
    """
    Handle completed embedded job: upload to S3 and send callback.
    If pending_effects exist, chain to GhostCut for text removal.
    """
    output_url = status_result.get("outputUrl")
    if not output_url:
        logger.error(f"Embedded job {job.id}: No output URL in completed response")
        return

    metadata = job.job_metadata or {}
    pending_effects = metadata.get("pending_effects", [])
    processing_type = metadata.get("processing_type", "lip_sync")

    logger.info(f"Embedded job {job.id}: Downloading lip-sync result...")

    try:
        # Download from Sync.so and upload to our S3
        s3_url = await embedded_processing_service.download_and_upload_result(
            output_url=output_url,
            user_id=phraze_user_id or "unknown",
            job_id=str(job.id)
        )

        logger.info(f"Embedded job {job.id}: Lip-sync output uploaded to S3")

        # Check if we need to chain to GhostCut for text removal
        if processing_type == "both" and pending_effects:
            await start_ghostcut_chain(
                job, s3_url, pending_effects,
                callback_url, phraze_job_id, phraze_user_id
            )
            return

        # No chaining needed - finalize the job
        await finalize_embedded_job(
            job, s3_url, callback_url, phraze_job_id
        )

    except Exception as e:
        logger.error(f"Embedded job {job.id}: Error handling completion: {e}")
        # Mark as failed and send failure callback
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()

        await PhrazeCallbackService.notify_job_failed(
            callback_url=callback_url,
            job_id=phraze_job_id,
            error_code="UPLOAD_FAILED",
            error_message=str(e),
            processing_time_seconds=0,
            metadata={"internal_job_id": str(job.id)}
        )


async def start_ghostcut_chain(
    job: VideoJob,
    lipsync_output_url: str,
    effects: list,
    callback_url: str,
    phraze_job_id: str,
    phraze_user_id: str
) -> None:
    """
    Chain to GhostCut for text removal after lip-sync completes.
    Updates job to poll for GhostCut instead of Sync.so.
    """
    from backend.api.routes.jobs.processing.ghostcut_api import (
        call_ghostcut_api_async
    )

    logger.info(
        f"Embedded job {job.id}: Chaining to GhostCut with "
        f"{len(effects)} effects for text removal"
    )

    try:
        # Call GhostCut API with the lip-synced video and effects
        ghostcut_task_id = await call_ghostcut_api_async(
            video_url=lipsync_output_url,
            job_id=str(job.id),
            effects_data=effects
        )

        logger.info(
            f"Embedded job {job.id}: GhostCut job created: {ghostcut_task_id}"
        )

        # Update job to track GhostCut instead of Sync.so
        job.zhaoli_task_id = ghostcut_task_id
        job.progress_percentage = 60
        job.progress_message = "Text removal processing..."

        # Update metadata to indicate we're now in GhostCut phase
        if not job.job_metadata:
            job.job_metadata = {}
        job.job_metadata["current_phase"] = "ghostcut"
        job.job_metadata["lipsync_output_url"] = lipsync_output_url
        job.job_metadata["pending_effects"] = []  # Clear since we've started
        flag_modified(job, 'job_metadata')

        # Celery will continue polling (now checking GhostCut status)
        logger.info(
            f"Embedded job {job.id}: Switched to GhostCut polling"
        )

    except Exception as e:
        logger.error(
            f"Embedded job {job.id}: Failed to start GhostCut: {e}"
        )
        # Fall back to just returning the lip-sync result
        logger.info(
            f"Embedded job {job.id}: Falling back to lip-sync only result"
        )
        await finalize_embedded_job(
            job, lipsync_output_url, callback_url, phraze_job_id,
            fallback_message="Lip-sync completed (text removal failed)"
        )


async def finalize_embedded_job(
    job: VideoJob,
    output_url: str,
    callback_url: str,
    phraze_job_id: str,
    fallback_message: str = None
) -> None:
    """
    Finalize embedded job: update status and send callback.
    """
    job.status = JobStatus.COMPLETED.value
    job.output_url = output_url
    job.progress_percentage = 100
    job.progress_message = fallback_message or "Processing completed!"
    job.completed_at = datetime.utcnow()

    logger.info(f"Embedded job {job.id}: Completed, output={output_url[:60]}...")

    # Calculate processing time
    processing_time = 0
    if job.started_at:
        processing_time = int((datetime.utcnow() - job.started_at).total_seconds())

    # Send completion callback to phraze.so
    await PhrazeCallbackService.notify_job_completed(
        callback_url=callback_url,
        job_id=phraze_job_id,
        output_url=output_url,
        processing_time_seconds=processing_time,
        metadata={
            "internal_job_id": str(job.id),
            "sync_generation_id": job.job_metadata.get("sync_generation_id")
        }
    )

    logger.info(f"Embedded job {job.id}: Callback sent to phraze.so")


async def handle_embedded_failure(
    job: VideoJob,
    status_result: dict,
    callback_url: str,
    phraze_job_id: str
) -> None:
    """
    Handle failed embedded job: update status and send failure callback
    """
    error_msg = status_result.get("error", "Unknown error")
    logger.error(f"Embedded job {job.id}: Sync.so failed: {error_msg}")

    job.status = JobStatus.FAILED.value
    job.error_message = error_msg
    job.progress_message = f"Lip-sync failed: {error_msg}"
    job.completed_at = datetime.utcnow()

    # Calculate processing time
    processing_time = 0
    if job.started_at:
        processing_time = int((datetime.utcnow() - job.started_at).total_seconds())

    # Send failure callback to phraze.so
    await PhrazeCallbackService.notify_job_failed(
        callback_url=callback_url,
        job_id=phraze_job_id,
        error_code="SYNC_FAILED",
        error_message=error_msg,
        processing_time_seconds=processing_time,
        metadata={"internal_job_id": str(job.id)}
    )

    logger.info(f"Embedded job {job.id}: Failure callback sent to phraze.so")


async def check_all_embedded_jobs(jobs: List[VideoJob]) -> None:
    """
    Check all embedded jobs asynchronously
    """
    tasks = [check_embedded_job(job) for job in jobs]
    await asyncio.gather(*tasks, return_exceptions=True)


def check_embedded_jobs_sync() -> None:
    """
    Periodic task to check embedded jobs and send callbacks
    """
    db = get_db()
    try:
        # Find embedded jobs that are processing with Sync.so generation ID
        embedded_jobs = db.query(VideoJob).filter(
            VideoJob.status == JobStatus.PROCESSING.value,
            VideoJob.is_embedded_job == True,
            VideoJob.zhaoli_task_id.isnot(None)
        ).all()

        if not embedded_jobs:
            logger.debug("No embedded jobs to check")
            return

        logger.info(f"Checking {len(embedded_jobs)} embedded jobs")

        # Run async checks
        asyncio.run(check_all_embedded_jobs(embedded_jobs))

        # Commit all changes
        db.commit()
        logger.info("Completed checking embedded jobs")

    except Exception as e:
        logger.error(f"Error in check_embedded_jobs: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


@app.task
def check_embedded_job_completion() -> None:
    """
    Celery task to check embedded job completion and send callbacks
    """
    check_embedded_jobs_sync()
