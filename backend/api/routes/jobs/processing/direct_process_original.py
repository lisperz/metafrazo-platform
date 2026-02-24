"""
Direct video processing without Celery - Immediate GhostCut API integration
Processes videos instantly when uploaded, no queue delays
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

logger = logging.getLogger(__name__)

router = APIRouter()

class DirectProcessResponse(BaseModel):
    job_id: str
    filename: str
    message: str
    status: str
    ghostcut_task_id: Optional[str] = None

class BatchProcessResponse(BaseModel):
    jobs: List[DirectProcessResponse]
    total_files: int
    message: str

async def call_ghostcut_api_async(video_url: str, job_id: str, effects_data: Optional[List] = None) -> str:
    """
    Directly call GhostCut API asynchronously - NO CELERY!
    Returns the GhostCut task ID immediately
    """
    
    # ALWAYS use the /free endpoint for both full-screen and annotation area processing
    url = f"{settings.ghostcut_api_url}/v-w-c/gateway/ve/work/free"
    
    # Prepare request data
    request_data = {
        "urls": [video_url],
        "uid": settings.ghostcut_uid,
        "workName": f"Processed_video_{job_id[:8]}",
        "resolution": "1080p",
        "videoInpaintLang": "all"
    }
    
    # Handle region-specific vs full-screen processing
    # Based on GhostCut API documentation:
    # - needChineseOcclude=0: Disabled
    # - needChineseOcclude=1: Full screen inpainting, can use videoInpaintMasks for protection (keep)
    # - needChineseOcclude=2: Complete inpainting according to videoInpaintMasks specified areas
    # - needChineseOcclude=3: Automatically remove detected text, can use videoInpaintMasks
    # - videoInpaintMasks: JSON string with region objects using normalized coordinates [x1,y1,x2,y2] (0-1 range)
    if effects_data and len(effects_data) > 0:
        # 🧪 DEBUG: Log incoming frontend parameters
        print("\n" + "=" * 80)
        print("🎯 PARAMETER CONVERSION VALIDATION")
        print("=" * 80)
        print(f"📥 FRONTEND PAYLOAD (Raw Effects):")
        print(json.dumps(effects_data, indent=2))
        print("=" * 80)
        
        logger.info("=" * 60)
        logger.info("🧪 FRONTEND PARAMETERS DEBUG")
        logger.info("=" * 60)
        logger.info(f"📊 Total effects received: {len(effects_data)}")
        for i, effect in enumerate(effects_data, 1):
            logger.info(f"🔍 Effect {i}: {json.dumps(effect, indent=2)}")
        logger.info("=" * 60)
        
        # Convert effects to GhostCut videoInpaintMasks format
        video_inpaint_masks = []
        
        # Map frontend effect types to GhostCut API types
        effect_type_mapping = {
            'erasure': 'remove',              # Erasure Area → remove
            'protection': 'keep',             # Protection Area → keep  
            'text': 'remove_only_ocr'         # Erase Text → remove_only_ocr
        }
        
        for effect in effects_data:
            effect_type = effect.get('type')
            if effect_type in effect_type_mapping:
                region = effect.get('region', {})
                if region and all(k in region for k in ['x', 'y', 'width', 'height']):
                    # Validate coordinates are in normalized range (0-1)
                    x1, y1 = region['x'], region['y']
                    x2, y2 = region['x'] + region['width'], region['y'] + region['height']
                    
                    # Ensure coordinates are within valid range [0, 1]
                    x1 = max(0.0, min(1.0, x1))
                    y1 = max(0.0, min(1.0, y1))
                    x2 = max(0.0, min(1.0, x2))
                    y2 = max(0.0, min(1.0, y2))
                    
                    # Ensure x2 > x1 and y2 > y1 (valid rectangle)
                    if x2 > x1 and y2 > y1:
                        # Extract timing information from effect (if available)
                        # Note: Frontend may send startTime/endTime or startFrame/endFrame
                        # Handle both property names for compatibility
                        start_time = effect.get('startTime') or effect.get('startFrame', 0)
                        end_time = effect.get('endTime') or effect.get('endFrame', 99999)
                        
                        # According to API docs, region should be normalized coordinates [0-1]
                        # Format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] - coordinate pairs for rectangle corners
                        mask_entry = {
                            "type": effect_type_mapping[effect_type],  # Map to correct GhostCut type
                            "start": start_time,  # Start time in seconds (with decimal precision)
                            "end": end_time,      # End time in seconds (with decimal precision)
                            "region": [
                                [round(x1, 2), round(y1, 2)],  # Top-left corner
                                [round(x2, 2), round(y1, 2)],  # Top-right corner
                                [round(x2, 2), round(y2, 2)],  # Bottom-right corner
                                [round(x1, 2), round(y2, 2)]   # Bottom-left corner
                            ]
                        }
                        video_inpaint_masks.append(mask_entry)
                        logger.info(f"Added {effect_type} mask with normalized coordinates:")
                        logger.info(f"  - Type: {effect_type_mapping[effect_type]}")
                        logger.info(f"  - Region corners: TL({x1:.2f},{y1:.2f}) TR({x2:.2f},{y1:.2f}) BR({x2:.2f},{y2:.2f}) BL({x1:.2f},{y2:.2f})")
                        logger.info(f"  - Time: {start_time}s to {end_time}s")
                    else:
                        logger.warning(f"Invalid region dimensions for {effect_type}: {region}")
                else:
                    logger.warning(f"Missing or invalid region data for {effect_type}: {region}")
        
        if video_inpaint_masks:
            # IMPORTANT: videoInpaintMasks must be a JSON string according to API docs
            request_data["videoInpaintMasks"] = json.dumps(video_inpaint_masks)
            
            # Determine needChineseOcclude based on mask types:
            # - If only "keep" masks exist: needChineseOcclude = 1 (full screen inpainting with protection)
            # - If "remove" or "remove_only_ocr" masks exist: needChineseOcclude = 2 (annotation area inpainting)
            mask_types = [mask["type"] for mask in video_inpaint_masks]
            has_remove_masks = any(mask_type in ["remove", "remove_only_ocr"] for mask_type in mask_types)
            has_only_keep_masks = all(mask_type == "keep" for mask_type in mask_types)
            
            if has_only_keep_masks:
                # Only protection masks - use full screen inpainting with protection
                request_data["needChineseOcclude"] = 1
                logger.info(f"✅ PROTECTION-ONLY PROCESSING: Using {len(video_inpaint_masks)} protection masks")
                logger.info(f"✅ needChineseOcclude = 1 (full-screen inpainting with protection)")
            else:
                # Has removal masks - use annotation area inpainting
                request_data["needChineseOcclude"] = 2
                logger.info(f"✅ REGION-SPECIFIC PROCESSING: Using {len(video_inpaint_masks)} annotation masks")
                logger.info(f"✅ needChineseOcclude = 2 (complete annotation area removal)")
            
            logger.info(f"✅ Mask types: {mask_types}")
            logger.info(f"✅ videoInpaintMasks: {json.dumps(video_inpaint_masks, indent=2)}")
            
            # 🧪 VALIDATION: Check expected values from screenshot
            logger.info("=" * 60)
            logger.info("🧪 VALIDATION CHECKS")
            logger.info("=" * 60)
            for i, mask in enumerate(video_inpaint_masks, 1):
                logger.info(f"✅ Mask {i} Validation:")
                logger.info(f"  Type: {mask['type']} (should be 'remove' for erasure)")
                logger.info(f"  Start: {mask['start']}s (from frontend startTime/startFrame)")
                logger.info(f"  End: {mask['end']}s (from frontend endTime/endFrame)")
                logger.info(f"  Region: {mask['region']} (coordinate pairs)")
                
                # Expected format validation (coordinate pairs)
                region = mask['region']
                if (len(region) == 4 and 
                    all(isinstance(coord_pair, list) and len(coord_pair) == 2 for coord_pair in region) and
                    all(isinstance(coord, (int, float)) for coord_pair in region for coord in coord_pair)):
                    # Extract coordinates from pairs
                    x_coords = [pair[0] for pair in region]
                    y_coords = [pair[1] for pair in region]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    if 0 <= x_min < x_max <= 1 and 0 <= y_min < y_max <= 1:
                        logger.info(f"  ✅ Region coordinate pairs valid and normalized")
                    else:
                        logger.warning(f"  ❌ Region coordinate pairs invalid: {region}")
                else:
                    logger.warning(f"  ❌ Region format invalid (expected 4 coordinate pairs): {region}")
            logger.info("=" * 60)
            
            # Print final converted parameters to console for validation
            print("\n" + "="*80)
            print("✅ FINAL CONVERTED PARAMETERS FOR GHOSTCUT API:")
            print("="*80)
            print(f"needChineseOcclude: {request_data.get('needChineseOcclude', 1)}")
            print(f"videoInpaintMasks: {json.dumps(video_inpaint_masks, indent=2)}")
            print("="*80 + "\n")
        else:
            # Fallback to full-screen if no valid regions
            request_data["needChineseOcclude"] = 1
            logger.warning("❌ NO VALID REGIONS: Falling back to full-screen inpainting")
            logger.warning("❌ needChineseOcclude = 1 (full-screen mode)")
    else:
        # Use full-screen text removal
        request_data["needChineseOcclude"] = 1
        logger.info("No effects data provided, using full-screen inpainting")
    
    # Log the full request data for debugging
    logger.info(f"📤 Full GhostCut API Request Data:")
    logger.info(f"📤 Using endpoint: {url}")
    logger.info(json.dumps(request_data, indent=2))
    
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
    
    logger.info(f"Calling GhostCut API directly for job {job_id}")
    
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
                
                logger.info(f"GhostCut job created immediately: {ghostcut_job_id}")
                return str(ghostcut_job_id)
            else:
                raise Exception(f"GhostCut API error: {result.get('msg', 'Unknown error')}")

async def process_video_immediately(
    job_id: str,
    file_path: str,
    db: Session,
    background_tasks: BackgroundTasks
):
    """
    Process video immediately without Celery
    """
    
    try:
        # Get job and user
        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
        user = db.query(User).filter(User.id == job.user_id).first()
        
        # Update status to processing
        job.status = JobStatus.PROCESSING.value
        job.started_at = datetime.datetime.now(datetime.timezone.utc)
        job.progress_percentage = 10
        job.progress_message = "Uploading to cloud storage..."
        db.commit()
        
        # Upload to S3 immediately
        filename = os.path.basename(file_path)
        s3_key = f"users/{user.id}/jobs/{job.id}/{filename}"
        
        logger.info(f"Uploading to S3: {s3_key}")
        video_url = s3_service.upload_video_and_get_url(file_path, s3_key)
        
        if not video_url:
            raise ValueError("Failed to upload video to S3")
        
        # Update progress
        job.progress_percentage = 30
        job.progress_message = "Submitting to AI processing..."
        job.job_metadata = {"s3_video_url": video_url, "s3_key": s3_key}
        db.commit()
        
        # Call GhostCut API immediately with effects data
        job_effects = job.processing_config.get('effects_data', [])
        ghostcut_task_id = await call_ghostcut_api_async(video_url, job_id, job_effects)
        
        # Update job with GhostCut task ID
        job.zhaoli_task_id = ghostcut_task_id
        job.progress_percentage = 50
        job.progress_message = "AI processing started successfully"
        db.commit()
        
        logger.info(f"Video {job_id} sent to GhostCut immediately with task ID: {ghostcut_task_id}")
        
        # Start background monitoring (non-blocking)
        background_tasks.add_task(monitor_ghostcut_status, job_id, ghostcut_task_id)
        
        return ghostcut_task_id
        
    except Exception as e:
        logger.error(f"Error processing video {job_id}: {e}")
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        raise

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

@router.post("/direct-process", response_model=DirectProcessResponse)
async def direct_process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    display_name: Optional[str] = Form(None),
    effects: Optional[str] = Form(None),  # JSON string of effects data
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Process video IMMEDIATELY without Celery queue
    Video is sent to GhostCut API instantly
    """
    
    # BASIC DEBUG - This should ALWAYS appear when function is called
    logger.info("🟢 FUNCTION START - direct_process_video called")
    
    logger.info("🚀 DIRECT PROCESS ENDPOINT CALLED!")
    logger.info(f"📄 File: {file.filename if file else 'No file'}")
    logger.info(f"📊 Effects: {effects}")
    
    # Debug - write to file immediately when endpoint is called
    import os
    debug_file = "/app/uploads/endpoint_debug.log"
    os.makedirs(os.path.dirname(debug_file), exist_ok=True)
    with open(debug_file, "a") as f:
        import datetime
        f.write(f"\n{'='*80}\n")
        f.write(f"Timestamp: {datetime.datetime.now()}\n")
        f.write(f"Endpoint called: /api/v1/direct/direct-process\n")
        f.write(f"File: {file.filename if file else 'No file'}\n")
        f.write(f"Effects received: {effects}\n")
        f.write(f"Effects type: {type(effects)}\n")
        f.write(f"Effects length: {len(effects) if effects else 0}\n")
        f.write(f"{'='*80}\n")
    
    # DEBUG: Always log when this endpoint is called
    logger.info("🔍 ENDPOINT CALLED - Checking effects parameter")
    logger.info(f"Effects provided: {effects is not None}")
    logger.info(f"Effects raw value: {repr(effects)}")
    
    # Show parameter conversion validation if effects are provided
    if effects:
        try:
            effects_data = json.loads(effects)
            
            # Use logger instead of print to ensure output appears in logs
            logger.info("\n" + "="*80)
            logger.info("🎯 PARAMETER CONVERSION VALIDATION")
            logger.info("="*80)
            logger.info(f"📥 FRONTEND PAYLOAD (Raw Effects):")
            logger.info(json.dumps(effects_data, indent=2))
            logger.info("="*80)
            
            # Convert to GhostCut format for validation
            video_inpaint_masks = []
            for effect in effects_data:
                if effect.get('type') == 'erasure':
                    region = effect.get('region', {})
                    if region and all(k in region for k in ['x', 'y', 'width', 'height']):
                        x1, y1 = region['x'], region['y']
                        x2, y2 = region['x'] + region['width'], region['y'] + region['height']
                        
                        # Clamp and round to 2 decimal places
                        x1 = round(max(0.0, min(1.0, x1)), 2)
                        y1 = round(max(0.0, min(1.0, y1)), 2)
                        x2 = round(max(0.0, min(1.0, x2)), 2)
                        y2 = round(max(0.0, min(1.0, y2)), 2)
                        
                        # Handle both startTime/endTime and startFrame/endFrame properties
                        start_time = effect.get('startTime') or effect.get('startFrame', 0)
                        end_time = effect.get('endTime') or effect.get('endFrame', 0)
                        
                        mask_entry = {
                            "type": "remove",
                            "start": round(start_time, 2),
                            "end": round(end_time, 2),
                            "region": [
                                [x1, y1],  # Top-left
                                [x2, y1],  # Top-right
                                [x2, y2],  # Bottom-right
                                [x1, y2]   # Bottom-left
                            ]
                        }
                        video_inpaint_masks.append(mask_entry)
            
            logger.info("📤 CONVERTED PARAMETERS FOR GHOSTCUT:")
            logger.info(json.dumps(video_inpaint_masks, indent=2))
            logger.info("="*80)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing effects JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Error during parameter conversion: {e}")
    
    # Use authenticated user from JWT token
    logger.info(f"🔐 Processing video for user: {current_user.email} (ID: {current_user.id})")
    
    # Validate file
    if file.size and file.size > 2 * 1024 * 1024 * 1024:  # 2GB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 2GB"
        )
    
    # Save file locally first
    file_id = uuid.uuid4()
    job_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    
    upload_dir = os.path.join(settings.upload_path, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Parse effects data if provided
    effects_data = []
    if effects:
        logger.info(f"🔍 RAW EFFECTS STRING RECEIVED: {effects}")
        try:
            effects_data = json.loads(effects)
            
            # Show parameter conversion validation
            print("\n" + "="*80)
            print("🎯 PARAMETER CONVERSION VALIDATION")
            print("="*80)
            print(f"📥 FRONTEND PAYLOAD (Raw Effects):")
            print(json.dumps(effects_data, indent=2))
            print("="*80)
            
            # Convert to GhostCut format for validation
            video_inpaint_masks = []
            for effect in effects_data:
                if effect.get('type') == 'erasure':
                    region = effect.get('region', {})
                    if region and all(k in region for k in ['x', 'y', 'width', 'height']):
                        x1, y1 = region['x'], region['y']
                        x2, y2 = region['x'] + region['width'], region['y'] + region['height']
                        
                        # Clamp and round to 2 decimal places
                        x1 = round(max(0.0, min(1.0, x1)), 2)
                        y1 = round(max(0.0, min(1.0, y1)), 2)
                        x2 = round(max(0.0, min(1.0, x2)), 2)
                        y2 = round(max(0.0, min(1.0, y2)), 2)
                        
                        # Handle both startTime/endTime and startFrame/endFrame properties
                        start_time = effect.get('startTime') or effect.get('startFrame', 0)
                        end_time = effect.get('endTime') or effect.get('endFrame', 0)
                        
                        mask_entry = {
                            "type": "remove",
                            "start": round(start_time, 2),
                            "end": round(end_time, 2),
                            "region": [
                                [x1, y1],  # Top-left
                                [x2, y1],  # Top-right
                                [x2, y2],  # Bottom-right
                                [x1, y2]   # Bottom-left
                            ]
                        }
                        video_inpaint_masks.append(mask_entry)
            
            print("\n✅ FINAL CONVERTED PARAMETERS FOR GHOSTCUT API:")
            print("="*80)
            print(f"needChineseOcclude: 2 (annotation area removal)")
            print(f"videoInpaintMasks: {json.dumps(video_inpaint_masks, indent=2)}")
            print("="*80 + "\n")
            
            # Force flush output
            import sys
            sys.stdout.flush()
            
            # Also log to logger
            logger.info(f"✅ CONVERTED PARAMETERS: needChineseOcclude=2, masks={json.dumps(video_inpaint_masks)}")
            
            # Write to file for debugging
            import os
            debug_file = "/app/uploads/parameter_conversion_debug.log"
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, "a") as f:
                import datetime
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.datetime.now()}\n")
                f.write(f"FRONTEND PAYLOAD:\n{json.dumps(effects_data, indent=2)}\n")
                f.write(f"\nCONVERTED PARAMETERS:\n")
                f.write(f"needChineseOcclude: 2\n")
                f.write(f"videoInpaintMasks:\n{json.dumps(video_inpaint_masks, indent=2)}\n")
                f.write(f"{'='*80}\n")
            
            logger.info(f"Parsed {len(effects_data)} effects for processing")
            logger.info(f"Effects data received: {effects_data}")
        except json.JSONDecodeError:
            logger.error(f"Invalid effects JSON: {effects}")
    else:
        logger.info("No effects data provided - will use full-screen processing")
    
    # Create database records
    db_file = File(
        id=file_id,
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_type=FileType.INPUT_VIDEO,
        mime_type=file.content_type,
        file_size_bytes=os.path.getsize(file_path),
        storage_path=file_path,
        storage_provider='local',
        is_public=False
    )
    db.add(db_file)
    
    job = VideoJob(
        id=job_id,
        user_id=current_user.id,
        original_filename=file.filename,
        display_name=display_name or f"Text Removal - {file.filename}",
        status=JobStatus.QUEUED.value,
        processing_config={
            "type": "direct_ghostcut",
            "local_video_path": file_path,
            "video_file_id": str(file_id),
            "effects_data": effects_data,  # Store the parsed effects data
        },
        estimated_credits=10,
        queued_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(job)
    db.commit()
    
    # Process immediately (no Celery!)
    logger.info(f"Processing video {job_id} IMMEDIATELY without queue")
    
    try:
        # This runs asynchronously but doesn't block the response
        ghostcut_task_id = await process_video_immediately(
            str(job_id),
            file_path,
            db,
            background_tasks
        )
        
        return DirectProcessResponse(
            job_id=str(job_id),
            filename=file.filename,
            message="Video sent to GhostCut API immediately! Processing started.",
            status="processing",
            ghostcut_task_id=ghostcut_task_id
        )
        
    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        return DirectProcessResponse(
            job_id=str(job_id),
            filename=file.filename,
            message=f"Failed to start processing: {str(e)}",
            status="failed",
            ghostcut_task_id=None
        )

@router.post("/batch-process", response_model=BatchProcessResponse)
async def batch_process_videos(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """
    Process MULTIPLE videos simultaneously
    All videos are sent to GhostCut API immediately
    """
    
    # Use authenticated user from JWT token
    logger.info(f"🔐 Processing batch videos for user: {current_user.email} (ID: {current_user.id})")
    
    jobs = []
    
    for file in files:
        # Process each file
        try:
            # Save file
            file_id = uuid.uuid4()
            job_id = uuid.uuid4()
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{file_id}{file_extension}"
            
            upload_dir = os.path.join(settings.upload_path, str(current_user.id))
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, unique_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create records
            db_file = File(
                id=file_id,
                user_id=current_user.id,
                filename=unique_filename,
                original_filename=file.filename,
                file_type=FileType.INPUT_VIDEO,
                mime_type=file.content_type or "video/mp4",
                file_size_bytes=os.path.getsize(file_path),
                storage_path=file_path,
                storage_provider='local',
                is_public=False
            )
            db.add(db_file)
            
            job = VideoJob(
                id=job_id,
                user_id=current_user.id,
                original_filename=file.filename,
                display_name=f"Text Removal - {file.filename}",
                status=JobStatus.QUEUED.value,
                processing_config={
                    "type": "direct_ghostcut",
                    "local_video_path": file_path,
                    "video_file_id": str(file_id),
                },
                estimated_credits=10,
                queued_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(job)
            db.commit()
            
            # Process immediately
            ghostcut_task_id = await process_video_immediately(
                str(job_id),
                file_path,
                db,
                background_tasks
            )
            
            jobs.append(DirectProcessResponse(
                job_id=str(job_id),
                filename=file.filename,
                message="Processing started",
                status="processing",
                ghostcut_task_id=ghostcut_task_id
            ))
            
        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {e}")
            jobs.append(DirectProcessResponse(
                job_id="",
                filename=file.filename,
                message=f"Failed: {str(e)}",
                status="failed",
                ghostcut_task_id=None
            ))
    
    return BatchProcessResponse(
        jobs=jobs,
        total_files=len(files),
        message=f"Processing {len([j for j in jobs if j.status == 'processing'])} videos"
    )

@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_database)):
    """
    Get real-time status of a processing job
    """
    
    job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If job has GhostCut task ID, check real status
    if job.zhaoli_task_id and job.status == JobStatus.PROCESSING.value:
        status = await check_ghostcut_status_async(job.zhaoli_task_id)
        
        # Update job with latest status
        if status["status"] == "completed":
            job.status = JobStatus.COMPLETED.value
            job.progress_percentage = 100
            job.progress_message = "Processing completed"
        elif status["status"] == "processing":
            job.progress_percentage = status.get("progress", 50)
            job.progress_message = f"Processing... {status.get('progress', 0)}%"
        
        db.commit()
    
    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress_percentage,
        "message": job.progress_message,
        "ghostcut_task_id": job.zhaoli_task_id,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }