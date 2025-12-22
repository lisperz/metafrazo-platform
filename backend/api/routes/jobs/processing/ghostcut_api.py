"""
Utility functions for direct_process routes
"""

import json
import hashlib
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from backend.config import settings

logger = logging.getLogger(__name__)





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



