"""
Pro video editor job processing (Sync.so integration with GhostCut chaining)
"""

import logging
import os
import uuid
import asyncio
import aiohttp
import tempfile
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.models.job import VideoJob, JobStatus
from backend.config import settings
from backend.workers.video_tasks.helpers import get_db
from backend.auth.phraze import PhrazeCallbackService

logger = logging.getLogger(__name__)


async def send_phraze_callback(job: VideoJob, output_url: str) -> None:
    """
    Send callback to Phraze.so when embedded job completes
    """
    if not job.is_embedded_job:
        return

    job_metadata = job.job_metadata or {}
    callback_url = job_metadata.get("phraze_callback_url")
    phraze_job_id = job_metadata.get("phraze_job_id")

    if not callback_url or not phraze_job_id:
        logger.warning(f"Job {job.id}: Missing callback info for embedded job")
        return

    # Calculate processing time
    processing_time = 0
    if job.started_at and job.completed_at:
        processing_time = int((job.completed_at - job.started_at).total_seconds())

    logger.info(f"Job {job.id}: Sending completion callback to {callback_url}")

    try:
        success = await PhrazeCallbackService.notify_job_completed(
            callback_url=callback_url,
            job_id=phraze_job_id,
            output_url=output_url,
            processing_time_seconds=processing_time,
            metadata={
                "internal_job_id": str(job.id),
                "processing_type": job_metadata.get("processing_type", "lip_sync")
            }
        )
        if success:
            logger.info(f"Job {job.id}: Phraze callback sent successfully")
        else:
            logger.error(f"Job {job.id}: Phraze callback failed")
    except Exception as e:
        logger.error(f"Job {job.id}: Error sending Phraze callback: {e}")


async def send_phraze_failure_callback(job: VideoJob, error_message: str) -> None:
    """
    Send failure callback to Phraze.so when embedded job fails
    """
    if not job.is_embedded_job:
        return

    job_metadata = job.job_metadata or {}
    callback_url = job_metadata.get("phraze_callback_url")
    phraze_job_id = job_metadata.get("phraze_job_id")

    if not callback_url or not phraze_job_id:
        return

    logger.info(f"Job {job.id}: Sending failure callback to {callback_url}")

    try:
        await PhrazeCallbackService.notify_job_failed(
            callback_url=callback_url,
            job_id=phraze_job_id,
            error_code="PROCESSING_FAILED",
            error_message=error_message,
            metadata={"internal_job_id": str(job.id)}
        )
    except Exception as e:
        logger.error(f"Job {job.id}: Error sending Phraze failure callback: {e}")


async def send_phraze_started_callback(job: VideoJob) -> None:
    """
    Send 'started' callback to Phraze.so when job starts processing
    This changes status from 'editing' to 'processing' in Phraze.so
    """
    if not job.is_embedded_job:
        return

    job_metadata = job.job_metadata or {}
    callback_url = job_metadata.get("phraze_callback_url")
    phraze_job_id = job_metadata.get("phraze_job_id")

    if not callback_url or not phraze_job_id:
        return

    logger.info(f"Job {job.id}: Sending 'started' callback to {callback_url}")

    try:
        await PhrazeCallbackService.notify_job_started(
            callback_url=callback_url,
            job_id=phraze_job_id,
            metadata={"internal_job_id": str(job.id)}
        )
        logger.info(f"Job {job.id}: Phraze 'started' callback sent successfully")
    except Exception as e:
        logger.error(f"Job {job.id}: Error sending Phraze started callback: {e}")


async def check_and_update_single_job(job: VideoJob) -> None:
    """
    Check and update a single Pro job status
    """
    try:
        from backend.services.sync_segments_service import sync_segments_service
        from backend.services.s3 import s3_service

        generation_id = job.zhaoli_task_id
        logger.info(f"Checking Sync.so generation {generation_id} for job {job.id}")

        # Check status with Sync.so
        status_result = await sync_segments_service.check_generation_status(
            generation_id
        )

        status = status_result.get('status')
        logger.info(f"Job {job.id}: Sync.so status = {status}")

        if status == 'COMPLETED':
            await handle_completed_job(job, status_result, s3_service)
        elif status in ['REJECTED', 'FAILED']:
            await handle_failed_job(job, status_result)
        elif status == 'PROCESSING':
            logger.info(f"Job {job.id}: Still processing on Sync.so")

    except Exception as e:
        logger.error(f"Error checking job {job.id}: {e}", exc_info=True)


async def handle_completed_job(
    job: VideoJob,
    status_result: dict,
    s3_service
) -> None:
    """
    Handle a completed Pro job

    This function implements chained processing:
    1. Download Sync.so result (lip-sync completed video)
    2. Upload to S3
    3. Check if annotation areas (text inpainting) are defined
    4. If yes: Submit to GhostCut API for text inpainting
    5. If no: Mark job as completed
    """
    output_url = status_result.get('outputUrl')
    if not output_url:
        logger.error(f"Job {job.id}: No output URL in completed response")
        return

    logger.info(f"Job {job.id}: Downloading Sync.so result from {output_url}")

    # Download the processed video from Sync.so
    async with aiohttp.ClientSession() as session:
        async with session.get(output_url) as response:
            if response.status == 200:
                video_data = await response.read()

                # Upload to S3
                output_filename = f"pro_sync_result_{job.id}.mp4"
                s3_key = f"users/{job.user_id}/jobs/{job.id}/{output_filename}"

                # Save temporarily
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix='.mp4'
                ) as tmp_file:
                    tmp_file.write(video_data)
                    tmp_path = tmp_file.name

                try:
                    # Upload Sync.so result to S3
                    sync_result_url = s3_service.upload_video_and_get_url(
                        tmp_path,
                        s3_key
                    )

                    if not sync_result_url:
                        logger.error(f"Job {job.id}: Failed to upload Sync.so result to S3")
                        return

                    logger.info(
                        f"Job {job.id}: Sync.so result uploaded to S3: {sync_result_url}"
                    )

                    # Check if annotation areas (text inpainting effects) are defined
                    processing_config = job.processing_config or {}
                    effects = processing_config.get('effects')

                    # Handle string-encoded effects (triple-encoding bug)
                    if effects and isinstance(effects, str):
                        try:
                            effects = json.loads(effects)
                            logger.warning(f"Job {job.id}: Effects were string-encoded, parsed to array")
                        except json.JSONDecodeError:
                            logger.error(f"Job {job.id}: Failed to parse string-encoded effects")
                            effects = []

                    has_annotation_areas = effects and isinstance(effects, list) and len(effects) > 0

                    if has_annotation_areas:
                        # Chain processing: Send to GhostCut for text inpainting
                        logger.info(
                            f"Job {job.id}: Found {len(effects)} annotation areas. "
                            "Starting GhostCut text inpainting..."
                        )

                        await start_ghostcut_processing(
                            job,
                            sync_result_url,
                            effects,
                            s3_service
                        )
                    else:
                        # No annotation areas - job is complete
                        logger.info(
                            f"Job {job.id}: No annotation areas defined. "
                            "Marking job as completed."
                        )

                        job.status = JobStatus.COMPLETED.value
                        job.output_url = sync_result_url
                        job.progress_percentage = 100
                        job.progress_message = "Pro video processing completed (lip-sync only)"
                        job.completed_at = datetime.utcnow()

                        logger.info(
                            f"Job {job.id}: Successfully completed at {sync_result_url}"
                        )

                        # Send callback to Phraze.so for embedded jobs
                        await send_phraze_callback(job, sync_result_url)

                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            else:
                logger.error(
                    f"Job {job.id}: Failed to download Sync.so result, "
                    f"status {response.status}"
                )


async def handle_failed_job(job: VideoJob, status_result: dict) -> None:
    """
    Handle a failed Pro job
    """
    error_msg = status_result.get('error', 'Unknown error')
    logger.error(f"Job {job.id}: Sync.so job failed: {error_msg}")

    job.status = JobStatus.FAILED.value
    job.progress_message = f"Lip-sync generation failed: {error_msg}"
    job.error_message = error_msg
    job.completed_at = datetime.utcnow()

    # Send failure callback to Phraze.so for embedded jobs
    await send_phraze_failure_callback(job, error_msg)


async def check_all_pro_jobs(pro_jobs: List[VideoJob]) -> None:
    """
    Check all Pro jobs asynchronously
    """
    tasks = [check_and_update_single_job(job) for job in pro_jobs]
    await asyncio.gather(*tasks, return_exceptions=True)


def check_pro_job_completion_sync() -> None:
    """
    Periodic task to check completion status of Pro video jobs

    This function handles two types of Pro jobs:
    1. Sync.so lip-sync jobs (check_and_update_single_job)
    2. GhostCut text inpainting jobs (check_ghostcut_pro_job_completion)
    """
    db = get_db()
    try:
        # Find all Pro jobs that are processing with Sync.so generation ID
        sync_jobs = db.query(VideoJob).filter(
            VideoJob.status == JobStatus.PROCESSING.value,
            VideoJob.is_pro_job == True,
            VideoJob.zhaoli_task_id.isnot(None),
            VideoJob.job_metadata['ghostcut_task_id'].astext.is_(None)  # Not yet in GhostCut phase
        ).all()

        # Find Pro jobs in GhostCut text inpainting phase
        ghostcut_jobs = db.query(VideoJob).filter(
            VideoJob.status == JobStatus.PROCESSING.value,
            VideoJob.is_pro_job == True,
            VideoJob.job_metadata['ghostcut_task_id'].astext.isnot(None)  # In GhostCut phase
        ).all()

        if not sync_jobs and not ghostcut_jobs:
            logger.info("No Pro jobs to check")
            return

        logger.info(
            f"Checking {len(sync_jobs)} Sync.so jobs and "
            f"{len(ghostcut_jobs)} GhostCut jobs"
        )

        # Check Sync.so jobs
        if sync_jobs:
            asyncio.run(check_all_pro_jobs(sync_jobs))

        # Check GhostCut jobs
        if ghostcut_jobs:
            asyncio.run(check_all_ghostcut_pro_jobs(ghostcut_jobs))

        # Commit all changes
        db.commit()
        logger.info("Completed checking Pro jobs")

    except Exception as e:
        logger.error(f"Error in check_pro_job_completion: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


async def start_ghostcut_processing(
    job: VideoJob,
    video_url: str,
    effects: List[Dict[str, Any]],
    s3_service
) -> None:
    """
    Start GhostCut text inpainting processing for Pro job

    This is called after Sync.so lip-sync completes successfully.
    """
    try:
        logger.info(
            f"Job {job.id}: Starting GhostCut processing with "
            f"{len(effects)} annotation areas"
        )

        # Update job metadata to track GhostCut phase
        job.progress_percentage = 60
        job.progress_message = "Lip-sync completed. Starting text inpainting..."

        # Call GhostCut API
        ghostcut_task_id = await call_ghostcut_api(
            video_url,
            str(job.id),
            effects
        )

        if ghostcut_task_id:
            # Update job metadata with GhostCut task ID
            if not job.job_metadata:
                job.job_metadata = {}
            job.job_metadata['ghostcut_task_id'] = ghostcut_task_id
            job.job_metadata['ghostcut_video_url'] = video_url

            # CRITICAL: Mark the JSONB field as modified so SQLAlchemy persists it
            flag_modified(job, 'job_metadata')

            job.progress_percentage = 70
            job.progress_message = "Text inpainting in progress..."

            logger.info(
                f"Job {job.id}: GhostCut task created: {ghostcut_task_id}. "
                "Will poll for completion."
            )
        else:
            logger.error(f"Job {job.id}: Failed to create GhostCut task")
            job.status = JobStatus.FAILED.value
            job.error_message = "Failed to start text inpainting"

    except Exception as e:
        logger.error(f"Job {job.id}: Error starting GhostCut processing: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = f"Failed to start text inpainting: {str(e)}"


async def call_ghostcut_api(
    video_url: str,
    job_id: str,
    effects: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Call GhostCut API for text inpainting

    Returns GhostCut task ID if successful, None otherwise
    """
    try:
        url = f"{settings.ghostcut_api_url}/v-w-c/gateway/ve/work/free"

        # Prepare request data
        request_data = {
            "urls": [video_url],
            "uid": settings.ghostcut_uid,
            "workName": f"Pro_Processed_{job_id[:8]}",
            "resolution": "1080p",
            "videoInpaintLang": "all"
        }

        # Convert effects to GhostCut videoInpaintMasks format
        video_inpaint_masks = []
        effect_type_mapping = {
            'erasure': 'remove',
            'protection': 'keep',
            'text': 'remove_only_ocr'
        }

        for effect in effects:
            effect_type = effect.get('type')
            if effect_type in effect_type_mapping:
                region = effect.get('region', {})
                if region and all(k in region for k in ['x', 'y', 'width', 'height']):
                    x1, y1 = region['x'], region['y']
                    x2, y2 = region['x'] + region['width'], region['y'] + region['height']

                    # Ensure valid coordinates [0, 1]
                    x1 = max(0.0, min(1.0, x1))
                    y1 = max(0.0, min(1.0, y1))
                    x2 = max(0.0, min(1.0, x2))
                    y2 = max(0.0, min(1.0, y2))

                    if x2 > x1 and y2 > y1:
                        start_time = effect.get('startTime', effect.get('startFrame', 0))
                        end_time = effect.get('endTime', effect.get('endFrame', 99999))

                        mask_entry = {
                            "type": effect_type_mapping[effect_type],
                            "start": start_time,
                            "end": end_time,
                            "region": [
                                [round(x1, 2), round(y1, 2)],
                                [round(x2, 2), round(y1, 2)],
                                [round(x2, 2), round(y2, 2)],
                                [round(x1, 2), round(y2, 2)]
                            ]
                        }
                        video_inpaint_masks.append(mask_entry)

        if video_inpaint_masks:
            request_data["videoInpaintMasks"] = json.dumps(video_inpaint_masks)

            # Determine processing mode
            mask_types = [mask["type"] for mask in video_inpaint_masks]
            has_only_keep_masks = all(mt == "keep" for mt in mask_types)

            request_data["needChineseOcclude"] = 1 if has_only_keep_masks else 2

            logger.info(
                f"GhostCut request: {len(video_inpaint_masks)} masks, "
                f"mode={request_data['needChineseOcclude']}"
            )
        else:
            request_data["needChineseOcclude"] = 1
            logger.warning("No valid masks, using full-screen mode")

        # Calculate signature
        body = json.dumps(request_data)
        md5_1 = hashlib.md5()
        md5_1.update(body.encode('utf-8'))
        body_md5hex = md5_1.hexdigest()
        md5_2 = hashlib.md5()
        body_md5hex = (body_md5hex + settings.ghostcut_app_secret).encode('utf-8')
        md5_2.update(body_md5hex)
        sign = md5_2.hexdigest()

        headers = {
            'Content-type': 'application/json',
            'AppKey': settings.ghostcut_api_key,
            'AppSign': sign,
        }

        # Call GhostCut API
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data, headers=headers, timeout=30) as response:
                result = await response.json()

                if result.get("code") == 1000:
                    body_data = result.get("body", {})
                    ghostcut_job_id = body_data.get("idProject")

                    if not ghostcut_job_id:
                        data_list = body_data.get("dataList", [])
                        if data_list:
                            ghostcut_job_id = data_list[0].get("id")

                    logger.info(f"GhostCut task created: {ghostcut_job_id}")
                    return str(ghostcut_job_id)
                else:
                    logger.error(f"GhostCut API error: {result.get('msg', 'Unknown error')}")
                    return None

    except Exception as e:
        logger.error(f"Error calling GhostCut API: {e}")
        return None


async def check_ghostcut_pro_job(job: VideoJob, s3_service) -> None:
    """
    Check GhostCut processing status for Pro job
    """
    try:
        ghostcut_task_id = job.job_metadata.get('ghostcut_task_id')
        if not ghostcut_task_id:
            logger.warning(f"Job {job.id}: No GhostCut task ID found")
            return

        logger.info(f"Job {job.id}: Checking GhostCut task {ghostcut_task_id}")

        # Check GhostCut status
        status_url = f"{settings.ghostcut_api_url}/v-w-c/gateway/ve/work/status"

        request_data = {"idProjects": [int(ghostcut_task_id)]}
        body = json.dumps(request_data)

        # Calculate signature
        md5_1 = hashlib.md5()
        md5_1.update(body.encode('utf-8'))
        body_md5hex = md5_1.hexdigest()
        md5_2 = hashlib.md5()
        body_md5hex = (body_md5hex + settings.ghostcut_app_secret).encode('utf-8')
        md5_2.update(body_md5hex)
        sign = md5_2.hexdigest()

        headers = {
            'Content-type': 'application/json',
            'AppKey': settings.ghostcut_api_key,
            'AppSign': sign,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(status_url, json=request_data, headers=headers, timeout=15) as response:
                logger.info(f"Job {job.id}: GhostCut HTTP status: {response.status}")

                response_text = await response.text()
                logger.info(f"Job {job.id}: GhostCut raw response: {response_text[:200]}")

                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Job {job.id}: Failed to parse GhostCut response as JSON: {e}")
                    return

                logger.info(f"Job {job.id}: GhostCut API response code: {result.get('code')}")

                if result.get("code") == 1000:
                    body_data = result.get("body", {})
                    content = body_data.get("content", [])

                    if not content:
                        logger.warning(f"Job {job.id}: No content in GhostCut response")
                        return

                    task_data = content[0]
                    process_status = task_data.get("processStatus", 0)
                    process_progress = task_data.get("processProgress", 0.0)
                    video_url = task_data.get("videoUrl", "")

                    logger.info(f"Job {job.id}: GhostCut processStatus={process_status}, progress={process_progress}%")

                    # Check if completed (progress >= 100)
                    if process_progress >= 100.0:
                        # Processing completed
                        logger.info(f"Job {job.id}: GhostCut completed! Downloading result...")
                        task_data_with_url = {"url": video_url, "resultUrl": video_url}
                        await handle_ghostcut_completion(job, task_data_with_url, s3_service)
                    elif process_status == -1:
                        # Processing failed
                        error_msg = task_data.get("errorMsg", "Unknown error")
                        logger.error(f"Job {job.id}: GhostCut failed: {error_msg}")
                        job.status = JobStatus.FAILED.value
                        job.error_message = f"Text inpainting failed: {error_msg}"
                    else:
                        # Still processing
                        job.progress_percentage = min(95, max(70, int(process_progress * 0.35 + 70)))
                        logger.info(f"Job {job.id}: GhostCut still processing (status={process_status}, progress={process_progress}%)")
                else:
                    logger.error(f"Job {job.id}: GhostCut API error: code={result.get('code')}, msg={result.get('msg')}")

    except Exception as e:
        logger.error(f"Job {job.id}: Error checking GhostCut status: {e}")


async def handle_ghostcut_completion(
    job: VideoJob,
    ghostcut_data: Dict[str, Any],
    s3_service
) -> None:
    """
    Handle GhostCut completion for Pro job
    """
    try:
        # Get result URL from GhostCut
        result_url = ghostcut_data.get("url") or ghostcut_data.get("resultUrl")

        if not result_url:
            logger.error(f"Job {job.id}: No result URL from GhostCut")
            job.status = JobStatus.FAILED.value
            job.error_message = "No output URL from text inpainting service"
            return

        logger.info(f"Job {job.id}: GhostCut completed. Downloading result from {result_url}")

        # Download the final processed video
        async with aiohttp.ClientSession() as session:
            async with session.get(result_url) as response:
                if response.status == 200:
                    video_data = await response.read()

                    # Upload final result to S3
                    final_filename = f"pro_final_result_{job.id}.mp4"
                    s3_key = f"users/{job.user_id}/jobs/{job.id}/{final_filename}"

                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(video_data)
                        tmp_path = tmp_file.name

                    try:
                        final_url = s3_service.upload_video_and_get_url(tmp_path, s3_key)

                        if final_url:
                            job.status = JobStatus.COMPLETED.value
                            job.output_url = final_url
                            job.progress_percentage = 100
                            job.progress_message = "Pro video processing completed (lip-sync + text inpainting)"
                            job.completed_at = datetime.utcnow()

                            logger.info(
                                f"Job {job.id}: Successfully completed with chained processing. "
                                f"Final result: {final_url}"
                            )

                            # Send callback to Phraze.so for embedded jobs
                            await send_phraze_callback(job, final_url)
                        else:
                            logger.error(f"Job {job.id}: Failed to upload final result to S3")
                            job.status = JobStatus.FAILED.value
                            job.error_message = "Failed to upload final result"

                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    logger.error(f"Job {job.id}: Failed to download GhostCut result (status {response.status})")
                    job.status = JobStatus.FAILED.value
                    job.error_message = f"Failed to download result (HTTP {response.status})"

    except Exception as e:
        logger.error(f"Job {job.id}: Error handling GhostCut completion: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = f"Error processing final result: {str(e)}"


async def check_all_ghostcut_pro_jobs(ghostcut_jobs: List[VideoJob]) -> None:
    """
    Check all GhostCut Pro jobs asynchronously
    """
    from backend.services.s3 import s3_service

    tasks = [check_ghostcut_pro_job(job, s3_service) for job in ghostcut_jobs]
    await asyncio.gather(*tasks, return_exceptions=True)
