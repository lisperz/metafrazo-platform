"""
Sync API integration for lip-sync processing workflow
Handles the complete workflow: upload files → sync API → poll status → get output URL → submit to GhostCut
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import datetime
import uuid
import os
import shutil
import logging
import asyncio
import aiohttp
import json
import hashlib

from backend.models.database import get_database, SessionLocal
from backend.models.user import User
from backend.models.file import File, FileType
from backend.models.job import VideoJob, JobStatus
from backend.auth.dependencies import get_current_user
from backend.services.s3 import s3_service
from backend.config import settings

# Note: sync.so does not provide a Python package
# Using direct HTTP requests for sync.so API integration

logger = logging.getLogger(__name__)

router = APIRouter()

class SyncProcessResponse(BaseModel):
    job_id: str
    filename: str
    message: str
    status: str
    sync_generation_id: Optional[str] = None

async def upload_files_to_s3(video_file_path: str, audio_file_path: Optional[str], user_id: str, job_id: str) -> dict:
    """
    Upload video and audio files to S3 and return URLs
    """
    try:
        # Upload video file
        video_filename = os.path.basename(video_file_path)
        video_s3_key = f"users/{user_id}/jobs/{job_id}/video_{video_filename}"

        logger.info(f"Uploading video to S3: {video_s3_key}")
        video_url = s3_service.upload_video_and_get_url(video_file_path, video_s3_key)

        if not video_url:
            raise ValueError("Failed to upload video to S3")

        urls = {"video_url": video_url}

        # Upload audio file if provided
        if audio_file_path and os.path.exists(audio_file_path):
            audio_filename = os.path.basename(audio_file_path)
            audio_s3_key = f"users/{user_id}/jobs/{job_id}/audio_{audio_filename}"

            logger.info(f"Uploading audio to S3: {audio_s3_key}")
            audio_url = s3_service.upload_video_and_get_url(audio_file_path, audio_s3_key)

            if not audio_url:
                raise ValueError("Failed to upload audio to S3")

            urls["audio_url"] = audio_url

        return urls

    except Exception as e:
        logger.error(f"Error uploading files to S3: {e}")
        raise

async def call_sync_api(video_url: str, audio_url: str) -> str:
    """
    Call sync.so API to create lip-sync generation using HTTP requests
    Returns the generation ID for polling
    """
    url = "https://api.sync.so/v2/generate"

    # Prepare request data based on the screenshot format
    request_data = {
        "model": "lipsync-2",
        "input": [
            {
                "type": "video",
                "url": video_url
            },
            {
                "type": "audio",
                "url": audio_url
            }
        ],
        "options": {
            "sync_mode": "loop"
        }
    }

    # Use the same API key as Pro video editor from settings
    sync_api_key = settings.sync_api_key
    if not sync_api_key:
        raise Exception("Sync.so API key not configured (SYNC_API_KEY)")

    headers = {
        "x-api-key": sync_api_key
    }

    logger.info(f"Calling sync API with data: {json.dumps(request_data, indent=2)}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data, headers=headers, timeout=60) as response:
            result = await response.json()

            logger.info(f"Sync API response: {json.dumps(result, indent=2)}")

            # Extract generation ID from response
            generation_id = result.get("id")
            if not generation_id:
                raise Exception(f"Sync API error: No generation ID returned. Response: {result}")

            logger.info(f"Sync generation created: {generation_id}")
            return generation_id

async def poll_sync_status(generation_id: str) -> dict:
    """
    Poll sync.so API to check generation status using HTTP requests
    Returns status info including output URL when completed
    """
    url = f"https://api.sync.so/v2/generate/{generation_id}"

    # Use the same API key as Pro video editor from settings
    sync_api_key = settings.sync_api_key
    if not sync_api_key:
        raise Exception("Sync.so API key not configured (SYNC_API_KEY)")

    headers = {
        "x-api-key": sync_api_key
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as response:
            result = await response.json()

            logger.info(f"Sync status response: {json.dumps(result, indent=2)}")

            status = result.get("status", "PENDING")

            if status == "COMPLETED":
                output_url = result.get("outputUrl")
                if not output_url:
                    raise Exception(f"Sync completed but no output URL found: {result}")

                return {"status": "completed", "output_url": output_url}
            elif status == "PENDING":
                return {"status": "pending"}
            elif status == "FAILED":
                error = result.get("error", "Unknown error")
                return {"status": "failed", "error": error}
            else:
                return {"status": "processing"}

async def call_ghostcut_with_sync_output(sync_output_url: str, job_id: str, effects_data: Optional[List] = None) -> str:
    """
    Call GhostCut API with the lip-synced video from sync API
    """

    # Use the same GhostCut integration as direct_process.py
    url = f"{settings.ghostcut_api_url}/v-w-c/gateway/ve/work/free"

    request_data = {
        "urls": [sync_output_url],  # Use sync output URL instead of original video
        "uid": settings.ghostcut_uid,
        "workName": f"LipSync_Processed_video_{job_id[:8]}",
        "resolution": "1080p",
        "videoInpaintLang": "all"
    }

    # Handle effects data same as direct_process.py
    if effects_data and len(effects_data) > 0:
        video_inpaint_masks = []

        effect_type_mapping = {
            'erasure': 'remove',
            'protection': 'keep',
            'text': 'remove_only_ocr'
        }

        for effect in effects_data:
            effect_type = effect.get('type')
            if effect_type in effect_type_mapping:
                region = effect.get('region', {})
                if region and all(k in region for k in ['x', 'y', 'width', 'height']):
                    x1, y1 = region['x'], region['y']
                    x2, y2 = region['x'] + region['width'], region['y'] + region['height']

                    x1 = max(0.0, min(1.0, x1))
                    y1 = max(0.0, min(1.0, y1))
                    x2 = max(0.0, min(1.0, x2))
                    y2 = max(0.0, min(1.0, y2))

                    if x2 > x1 and y2 > y1:
                        start_time = effect.get('startTime') or effect.get('startFrame', 0)
                        end_time = effect.get('endTime') or effect.get('endFrame', 99999)

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
            request_data["needChineseOcclude"] = 2  # Annotation area inpainting
        else:
            request_data["needChineseOcclude"] = 1  # Full-screen inpainting
    else:
        request_data["needChineseOcclude"] = 1

    # Calculate signature (same as direct_process.py)
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

    logger.info(f"Calling GhostCut API with lip-synced video: {sync_output_url}")

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

                logger.info(f"GhostCut job created for lip-synced video: {ghostcut_job_id}")
                return str(ghostcut_job_id)
            else:
                raise Exception(f"GhostCut API error: {result.get('msg', 'Unknown error')}")

async def process_sync_workflow(
    job_id: str,
    video_file_path: str,
    audio_file_path: str,
    effects_data: List,
    db: Session,
    background_tasks: BackgroundTasks
):
    """
    Process the complete sync workflow:
    1. Upload video and audio to S3
    2. Call sync API
    3. Poll for completion
    4. Submit to GhostCut API
    """

    try:
        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
        user = db.query(User).filter(User.id == job.user_id).first()

        # Update status
        job.status = JobStatus.PROCESSING.value
        job.started_at = datetime.datetime.now(datetime.timezone.utc)
        job.progress_percentage = 10
        job.progress_message = "Uploading files to cloud storage..."
        db.commit()

        # Step 1: Upload files to S3
        urls = await upload_files_to_s3(video_file_path, audio_file_path, str(user.id), job_id)

        job.progress_percentage = 30
        job.progress_message = "Creating lip-sync generation..."
        job.job_metadata = urls
        db.commit()

        # Step 2: Call sync API
        sync_generation_id = await call_sync_api(urls["video_url"], urls["audio_url"])

        job.progress_percentage = 40
        job.progress_message = "Lip-sync processing started..."
        job.job_metadata.update({"sync_generation_id": sync_generation_id})
        db.commit()

        # Step 3: Poll for completion (in background)
        background_tasks.add_task(monitor_sync_and_ghostcut, job_id, sync_generation_id, effects_data)

        return sync_generation_id

    except Exception as e:
        logger.error(f"Error in sync workflow {job_id}: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        raise

async def monitor_sync_and_ghostcut(job_id: str, sync_generation_id: str, effects_data: List):
    """
    Background task to monitor sync processing and then submit to GhostCut
    """
    db = SessionLocal()
    try:
        # Monitor sync API until completion
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            status = await poll_sync_status(sync_generation_id)

            job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
            if not job:
                break

            if status["status"] == "completed":
                # Sync completed, now submit to GhostCut
                job.progress_percentage = 70
                job.progress_message = "Lip-sync completed, starting text removal..."
                db.commit()

                sync_output_url = status["output_url"]
                logger.info(f"Sync completed for job {job_id}, output URL: {sync_output_url}")

                # Submit to GhostCut API
                ghostcut_task_id = await call_ghostcut_with_sync_output(sync_output_url, job_id, effects_data)

                job.zhaoli_task_id = ghostcut_task_id
                job.progress_percentage = 80
                job.progress_message = "Text removal processing started..."
                job.job_metadata.update({
                    "sync_output_url": sync_output_url,
                    "ghostcut_task_id": ghostcut_task_id
                })
                db.commit()

                # Continue monitoring GhostCut
                await monitor_ghostcut_final_processing(job_id, ghostcut_task_id, db)
                break

            elif status["status"] == "failed":
                job.status = JobStatus.FAILED.value
                job.error_message = status.get("error", "Sync processing failed")
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                logger.error(f"Sync job {job_id} failed: {status.get('error')}")
                break
            else:
                # Still processing
                job.progress_percentage = min(50 + status.get("progress", 0) / 2, 65)
                job.progress_message = "Lip-sync processing..."
                db.commit()

    except Exception as e:
        logger.error(f"Error monitoring sync job {job_id}: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
    finally:
        db.close()

async def monitor_ghostcut_final_processing(job_id: str, ghostcut_task_id: str, db: Session):
    """
    Monitor GhostCut processing after sync completion
    """
    # Import the status checking function from direct_process_original.py
    from backend.api.routes.jobs.processing.direct_process_original import check_ghostcut_status_async

    try:
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            status = await check_ghostcut_status_async(ghostcut_task_id)

            job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
            if not job:
                break

            if status["status"] == "completed":
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                job.progress_percentage = 100
                job.progress_message = "Lip-sync and text removal completed!"

                if "output_url" in status:
                    job.output_url = status["output_url"]
                    logger.info(f"Job {job_id} completed with final output URL: {status['output_url']}")

                db.commit()
                break

            elif status["status"] == "failed":
                job.status = JobStatus.FAILED.value
                job.error_message = status.get("error", "Text removal processing failed")
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                logger.error(f"GhostCut processing failed for job {job_id}: {status.get('error')}")
                break
            else:
                # Still processing
                job.progress_percentage = min(80 + status.get("progress", 0) / 5, 95)
                job.progress_message = f"Text removal processing... {status.get('progress', 0)}%"
                db.commit()

    except Exception as e:
        logger.error(f"Error monitoring GhostCut for job {job_id}: {e}")

@router.post("/sync-process", response_model=SyncProcessResponse)
async def sync_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    audio: Optional[UploadFile] = FastAPIFile(None),
    display_name: Optional[str] = Form(None),
    effects: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Process video with lip-sync workflow:
    1. Upload video and audio files
    2. Create lip-sync with sync.so API
    3. Submit result to GhostCut for text removal
    """

    logger.info("🚀 SYNC PROCESS ENDPOINT CALLED!")
    logger.info(f"📄 Video: {file.filename if file else 'No file'}")
    logger.info(f"🎵 Audio: {audio.filename if audio else 'No audio'}")
    logger.info(f"📊 Effects: {effects}")

    # Validate audio file is provided
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is required for lip-sync processing"
        )

    # Validate file sizes
    if file.size and file.size > 2 * 1024 * 1024 * 1024:  # 2GB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Video file size exceeds 2GB"
        )

    if audio.size and audio.size > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file size exceeds 100MB"
        )

    # Save files locally first
    file_id = uuid.uuid4()
    audio_id = uuid.uuid4()
    job_id = uuid.uuid4()

    video_extension = os.path.splitext(file.filename)[1]
    audio_extension = os.path.splitext(audio.filename)[1]

    unique_video_filename = f"{file_id}{video_extension}"
    unique_audio_filename = f"{audio_id}{audio_extension}"

    upload_dir = os.path.join(settings.upload_path, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    video_file_path = os.path.join(upload_dir, unique_video_filename)
    audio_file_path = os.path.join(upload_dir, unique_audio_filename)

    try:
        # Save video file
        with open(video_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Save audio file
        with open(audio_file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save files: {str(e)}"
        )

    # Parse effects data
    effects_data = []
    if effects:
        try:
            effects_data = json.loads(effects)
            logger.info(f"Parsed {len(effects_data)} effects for sync processing")
        except json.JSONDecodeError:
            logger.error(f"Invalid effects JSON: {effects}")

    # Create database records
    db_video_file = File(
        id=file_id,
        user_id=current_user.id,
        filename=unique_video_filename,
        original_filename=file.filename,
        file_type=FileType.INPUT_VIDEO,
        mime_type=file.content_type,
        file_size_bytes=os.path.getsize(video_file_path),
        storage_path=video_file_path,
        storage_provider='local',
        is_public=False
    )
    db.add(db_video_file)

    db_audio_file = File(
        id=audio_id,
        user_id=current_user.id,
        filename=unique_audio_filename,
        original_filename=audio.filename,
        file_type=FileType.INPUT_VIDEO,  # Reuse this type for audio
        mime_type=audio.content_type,
        file_size_bytes=os.path.getsize(audio_file_path),
        storage_path=audio_file_path,
        storage_provider='local',
        is_public=False
    )
    db.add(db_audio_file)

    job = VideoJob(
        id=job_id,
        user_id=current_user.id,
        original_filename=file.filename,
        display_name=display_name or f"Lip-sync + Text Removal - {file.filename}",
        status=JobStatus.QUEUED.value,
        processing_config={
            "type": "sync_workflow",
            "video_file_path": video_file_path,
            "audio_file_path": audio_file_path,
            "video_file_id": str(file_id),
            "audio_file_id": str(audio_id),
            "effects_data": effects_data,
        },
        estimated_credits=20,  # Higher cost for lip-sync + text removal
        queued_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(job)
    db.commit()

    # Start sync workflow
    logger.info(f"Starting sync workflow for job {job_id}")

    try:
        sync_generation_id = await process_sync_workflow(
            str(job_id),
            video_file_path,
            audio_file_path,
            effects_data,
            db,
            background_tasks
        )

        return SyncProcessResponse(
            job_id=str(job_id),
            filename=file.filename,
            message="Lip-sync workflow started! Video and audio uploaded, processing initiated.",
            status="processing",
            sync_generation_id=sync_generation_id
        )

    except Exception as e:
        logger.error(f"Failed to start sync workflow: {e}")
        return SyncProcessResponse(
            job_id=str(job_id),
            filename=file.filename,
            message=f"Failed to start sync workflow: {str(e)}",
            status="failed",
            sync_generation_id=None
        )

@router.get("/sync-status/{job_id}")
async def get_sync_job_status(job_id: str, db: Session = Depends(get_database)):
    """
    Get real-time status of a sync workflow job
    """

    job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get metadata for additional info
    metadata = job.job_metadata or {}

    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress_percentage,
        "message": job.progress_message,
        "sync_generation_id": metadata.get("sync_generation_id"),
        "ghostcut_task_id": job.zhaoli_task_id,
        "video_url": metadata.get("video_url"),
        "audio_url": metadata.get("audio_url"),
        "sync_output_url": metadata.get("sync_output_url"),
        "final_output_url": job.output_url,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }