"""
Utility functions for direct_process routes
"""

import json
import hashlib
import uuid
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from backend.config import settings
from backend.models.database import SessionLocal
from backend.models.job import VideoJob, JobStatus

logger = logging.getLogger(__name__)





async def monitor_ghostcut_status(job_id: str, ghostcut_task_id: str):
    """
    Background task to monitor GhostCut processing status
    """
    db = SessionLocal()
    try:
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Check status from GhostCut
            status = await check_ghostcut_status_async(ghostcut_task_id)

            job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
            if not job:
                break

            if status["status"] == "completed":
                # Download result and update job
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                job.progress_percentage = 100
                job.progress_message = "Processing completed successfully"

                # Save the output URL for download
                if "output_url" in status:
                    job.output_url = status["output_url"]
                    logger.info(f"Job {job_id} completed with output URL: {status['output_url']}")

                db.commit()
                logger.info(f"Job {job_id} completed successfully")
                break

            elif status["status"] == "failed":
                job.status = JobStatus.FAILED.value
                job.error_message = status.get("error", "Processing failed")
                job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                logger.error(f"Job {job_id} failed: {status.get('error')}")
                break
            else:
                # Still processing
                job.progress_percentage = min(status.get("progress", 50), 90)
                job.progress_message = f"AI processing... {status.get('progress', 0)}%"
                db.commit()

    except Exception as e:
        logger.error(f"Error monitoring job {job_id}: {e}")
    finally:
        db.close()



async def check_ghostcut_status_async(ghostcut_task_id: str) -> dict:
    """
    Check GhostCut job status asynchronously
    """
    url = f"{settings.ghostcut_api_url}/v-w-c/gateway/ve/work/status"

    request_data = {"idProjects": [int(ghostcut_task_id)]}
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

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data, headers=headers, timeout=30) as response:
            result = await response.json()

            if result.get("code") == 1000:
                content = result.get("body", {}).get("content", [])
                if content:
                    task_data = content[0]
                    process_progress = task_data.get("processProgress", 0.0)
                    video_url = task_data.get("videoUrl", "")

                    if process_progress >= 100.0:
                        return {"status": "completed", "output_url": video_url, "progress": 100}
                    elif process_progress > 0:
                        return {"status": "processing", "progress": int(process_progress)}
                    else:
                        return {"status": "pending", "progress": 0}

            return {"status": "error", "error": result.get("msg", "Unknown error")}
