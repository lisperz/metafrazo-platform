"""
Celery tasks for embedded video processing (phraze.so integration)
Handles Sync.so polling and phraze.so callback sending
"""

import logging
import asyncio
from datetime import datetime
from typing import List

from backend.workers.celery_app import app
from backend.models.job import VideoJob, JobStatus
from backend.workers.video_tasks.helpers import get_db
from backend.services.embedded_processing import embedded_processing_service
from backend.auth.phraze import PhrazeCallbackService

logger = logging.getLogger(__name__)


async def check_embedded_job(job: VideoJob) -> None:
    """
    Check status of an embedded job and send callback if completed/failed
    """
    try:
        generation_id = job.zhaoli_task_id
        if not generation_id:
            logger.warning(f"Embedded job {job.id}: No generation ID found")
            return

        metadata = job.job_metadata or {}
        callback_url = metadata.get("phraze_callback_url")
        phraze_job_id = metadata.get("phraze_job_id")
        phraze_user_id = metadata.get("phraze_user_id")

        if not callback_url or not phraze_job_id:
            logger.warning(f"Embedded job {job.id}: Missing callback info")
            return

        logger.info(f"Checking embedded job {job.id}: generation={generation_id}")

        # Check Sync.so status
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
            job.progress_percentage = min(job.progress_percentage + 5, 80)
            job.progress_message = "Sync.so processing..."

    except Exception as e:
        logger.error(f"Error checking embedded job {job.id}: {e}", exc_info=True)


async def handle_embedded_completion(
    job: VideoJob,
    status_result: dict,
    callback_url: str,
    phraze_job_id: str,
    phraze_user_id: str
) -> None:
    """
    Handle completed embedded job: upload to S3 and send callback
    """
    output_url = status_result.get("outputUrl")
    if not output_url:
        logger.error(f"Embedded job {job.id}: No output URL in completed response")
        return

    logger.info(f"Embedded job {job.id}: Downloading and uploading result...")

    try:
        # Download from Sync.so and upload to our S3
        s3_url = await embedded_processing_service.download_and_upload_result(
            output_url=output_url,
            user_id=phraze_user_id or "unknown",
            job_id=str(job.id)
        )

        # Update job status
        job.status = JobStatus.COMPLETED.value
        job.output_url = s3_url
        job.progress_percentage = 100
        job.progress_message = "Lip-sync processing completed!"
        job.completed_at = datetime.utcnow()

        logger.info(f"Embedded job {job.id}: Completed, output={s3_url[:60]}...")

        # Calculate processing time
        processing_time = 0
        if job.started_at:
            processing_time = int((datetime.utcnow() - job.started_at).total_seconds())

        # Send completion callback to phraze.so
        await PhrazeCallbackService.notify_job_completed(
            callback_url=callback_url,
            job_id=phraze_job_id,
            output_url=s3_url,
            processing_time_seconds=processing_time,
            metadata={
                "internal_job_id": str(job.id),
                "sync_generation_id": job.zhaoli_task_id
            }
        )

        logger.info(f"Embedded job {job.id}: Callback sent to phraze.so")

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
