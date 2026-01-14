"""
Embedded video processing service for phraze.so integration
Handles real Sync.so API calls for lip-sync processing
"""

import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.config import settings
from backend.services.sync_segments_service import sync_segments_service
from backend.services.s3 import s3_service

logger = logging.getLogger(__name__)


class EmbeddedProcessingService:
    """
    Service for processing embedded videos from phraze.so
    Uses real Sync.so API for lip-sync generation
    """

    def __init__(self):
        self.sync_api_base = "https://api.sync.so"
        self.sync_api_key = settings.sync_api_key

    async def create_lipsync_generation(
        self,
        video_url: str,
        segments: List[Dict[str, Any]],
        audio_url_mapping: Dict[str, str],
        video_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a Sync.so lip-sync generation with segments

        Args:
            video_url: S3 URL of the input video
            segments: List of segment configurations with audioInput references
            audio_url_mapping: Dict mapping refId -> audio S3 URL
            video_metadata: Optional dict with fps, total_frames, width, height
                           for building bounding_boxes array (speaker selection)

        Returns:
            Sync.so generation ID for polling
        """
        try:
            logger.info(f"Creating Sync.so generation: video={video_url[:50]}...")
            logger.info(f"Segments: {len(segments)}, Audio files: {len(audio_url_mapping)}")

            # Check if any segment has speaker box
            has_speaker_boxes = any(
                seg.get("speakerBox") and seg["speakerBox"].get("method") == "manual"
                for seg in segments
            )
            if has_speaker_boxes:
                logger.info("Segments contain speaker boxes - will build bounding_boxes array")
                if video_metadata:
                    logger.info(f"Video metadata: {video_metadata}")
                else:
                    logger.warning("No video metadata provided - speaker boxes will be ignored")

            # Use the existing sync_segments_service for segment-based lip-sync
            response = await sync_segments_service.create_segmented_lipsync(
                video_url=video_url,
                segments=segments,
                audio_url_mapping=audio_url_mapping,
                video_metadata=video_metadata
            )

            generation_id = response.get("id")
            if not generation_id:
                raise ValueError(f"No generation ID in Sync.so response: {response}")

            logger.info(f"Sync.so generation created: {generation_id}")
            return generation_id

        except Exception as e:
            logger.error(f"Failed to create Sync.so generation: {e}")
            raise

    async def create_simple_lipsync(
        self,
        video_url: str,
        audio_url: str
    ) -> str:
        """
        Create a simple Sync.so lip-sync generation (single audio, full video)

        Args:
            video_url: S3 URL of the input video
            audio_url: S3 URL of the audio file

        Returns:
            Sync.so generation ID for polling
        """
        try:
            logger.info(f"Creating simple Sync.so generation")

            if not self.sync_api_key:
                raise ValueError("Sync.so API key not configured")

            payload = {
                "model": "lipsync-2",
                "input": [
                    {"type": "video", "url": video_url},
                    {"type": "audio", "url": audio_url}
                ],
                "options": {"sync_mode": "loop"}
            }

            headers = {
                "x-api-key": self.sync_api_key,
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.sync_api_base}/v2/generate",
                    json=payload,
                    headers=headers
                ) as response:
                    result = await response.json()

                    if response.status in [200, 201]:
                        generation_id = result.get("id")
                        logger.info(f"Simple Sync.so generation created: {generation_id}")
                        return generation_id
                    else:
                        raise Exception(f"Sync.so API error: {result}")

        except Exception as e:
            logger.error(f"Failed to create simple Sync.so generation: {e}")
            raise

    async def check_generation_status(self, generation_id: str) -> Dict[str, Any]:
        """
        Check Sync.so generation status

        Returns:
            Dict with status, outputUrl (if completed), error (if failed)
        """
        return await sync_segments_service.check_generation_status(generation_id)

    async def download_and_upload_result(
        self,
        output_url: str,
        user_id: str,
        job_id: str
    ) -> str:
        """
        Download Sync.so result and upload to our S3

        Args:
            output_url: Sync.so output video URL
            user_id: Phraze user ID (for S3 path)
            job_id: Internal job ID

        Returns:
            S3 URL of uploaded result
        """
        import tempfile
        import os

        try:
            logger.info(f"Downloading Sync.so result: {output_url[:60]}...")

            async with aiohttp.ClientSession() as session:
                async with session.get(output_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download: HTTP {response.status}")

                    video_data = await response.read()

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                tmp.write(video_data)
                tmp_path = tmp.name

            try:
                # Upload to S3
                s3_key = f"embedded/{user_id}/jobs/{job_id}/output.mp4"
                s3_url = s3_service.upload_video_and_get_url(tmp_path, s3_key)

                if not s3_url:
                    raise Exception("S3 upload failed")

                logger.info(f"Uploaded result to S3: {s3_url[:60]}...")
                return s3_url

            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Failed to download/upload result: {e}")
            raise


# Global service instance
embedded_processing_service = EmbeddedProcessingService()
