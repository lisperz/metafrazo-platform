"""
Sync.so API integration for segment-based lip-sync processing
Real implementation using Sync.so segments API documentation
"""

import logging
import aiohttp
import json
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SyncSegmentsService:
    """
    Service for calling Sync.so API with segment-based lip-sync

    API Documentation: https://docs.sync.so/developer-guides/segments
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sync.so segments service

        Args:
            api_key: Sync.so API key for authentication
        """
        self.api_key = api_key
        self.api_base_url = "https://api.sync.so"
        self.generations_endpoint = f"{self.api_base_url}/v2/generate"
        logger.info(f"SyncSegmentsService initialized (API key: {'configured' if api_key else 'not set'})")

    async def create_segmented_lipsync(
        self,
        video_url: str,
        segments: List[dict],
        audio_url_mapping: Dict[str, str]
    ) -> dict:
        """
        Create a lip-sync generation with multiple segments

        API Reference: https://docs.sync.so/developer-guides/segments

        Args:
            video_url: S3 URL of the video file
            segments: List of segment configurations from frontend
            audio_url_mapping: Dict mapping refId -> S3 URL for audio files

        Returns:
            dict: Sync.so API response containing generation_id and status

        Example segments structure:
        [
            {
                "startTime": 0.0,
                "endTime": 15.0,
                "audioInput": {
                    "refId": "audio-1",
                    "startTime": 2.0,  # Optional audio crop
                    "endTime": 12.0    # Optional audio crop
                },
                "label": "Intro Segment"
            }
        ]
        """
        try:
            # Build input array: video + all audio files with refIds
            input_array = [
                {
                    "type": "video",
                    "url": video_url
                }
            ]

            # Get unique audio refIds and add to input array
            unique_ref_ids = {seg["audioInput"]["refId"] for seg in segments}
            for ref_id in unique_ref_ids:
                if ref_id not in audio_url_mapping:
                    raise ValueError(f"Audio refId '{ref_id}' not found in uploaded files")

                input_array.append({
                    "type": "audio",
                    "url": audio_url_mapping[ref_id],
                    "refId": ref_id
                })

            logger.info(f"Built input array: 1 video + {len(unique_ref_ids)} audio files")

            # Build segments array for Sync.so API
            segments_array = []
            for i, seg in enumerate(segments):
                logger.info(f"Processing segment {i}: raw segment data = {json.dumps(seg, indent=2)}")

                segment_dict = {
                    "startTime": seg["startTime"],
                    "endTime": seg["endTime"],
                    "audioInput": {
                        "refId": seg["audioInput"]["refId"]
                    }
                }

                # Add optional audio crop times if present
                audio_input = seg["audioInput"]
                logger.info(
                    f"Segment {i} audioInput: startTime={audio_input.get('startTime')}, "
                    f"endTime={audio_input.get('endTime')}, type(startTime)={type(audio_input.get('startTime'))}"
                )

                if audio_input.get("startTime") is not None:
                    segment_dict["audioInput"]["startTime"] = audio_input["startTime"]
                if audio_input.get("endTime") is not None:
                    segment_dict["audioInput"]["endTime"] = audio_input["endTime"]

                logger.info(f"Segment {i} final dict: {json.dumps(segment_dict, indent=2)}")
                segments_array.append(segment_dict)

            # Build final API request payload
            payload = {
                "model": "lipsync-2-pro",  # Pro model for higher quality lip-sync
                "input": input_array,
                "segments": segments_array,
                "options": {
                    "sync_mode": "remap"  # Remap works correctly when audio crop times match segment times
                }
            }

            logger.info(f"Creating segmented lip-sync with {len(segments)} segments")
            logger.info(f"Sync.so API payload: {json.dumps(payload, indent=2)}")

            # Call Sync.so API
            if not self.api_key:
                logger.error("Sync.so API key not configured!")
                raise ValueError("Sync.so API key is required but not configured")

            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }

                async with session.post(
                    self.generations_endpoint,
                    json=payload,
                    headers=headers
                ) as response:
                    response_text = await response.text()

                    if response.status == 200 or response.status == 201:
                        result = json.loads(response_text)
                        generation_id = result.get("id")
                        logger.info(f"Sync.so generation created successfully: {generation_id}")
                        return result
                    else:
                        logger.error(f"Sync.so API error (status {response.status}): {response_text}")
                        raise Exception(
                            f"Sync.so API returned status {response.status}: {response_text}"
                        )

        except ValueError as e:
            logger.error(f"Validation error in create_segmented_lipsync: {e}")
            raise

        except Exception as e:
            logger.error(f"Error calling Sync.so API with segments: {e}")
            raise

    async def check_generation_status(self, generation_id: str) -> dict:
        """
        Check status of a Sync.so generation

        Args:
            generation_id: Sync.so generation ID

        Returns:
            dict with status, progress, and result URL if completed

        Status values: "queued", "processing", "completed", "failed"
        """
        try:
            logger.info(f"Checking generation status: {generation_id}")

            if not self.api_key:
                raise ValueError("Sync.so API key is required but not configured")

            status_url = f"{self.api_base_url}/v2/generate/{generation_id}"

            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }

                async with session.get(status_url, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        result = json.loads(response_text)
                        status = result.get("status", "unknown")
                        logger.info(f"Generation {generation_id} status: {status}")
                        return result
                    else:
                        logger.error(f"Status check failed (status {response.status}): {response_text}")
                        raise Exception(
                            f"Sync.so status check failed with status {response.status}: {response_text}"
                        )

        except Exception as e:
            logger.error(f"Error checking generation status: {e}")
            raise

    async def download_result(self, result_url: str, local_path: str) -> str:
        """
        Download processed video from Sync.so

        Args:
            result_url: URL to download the processed video
            local_path: Local path to save the file

        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading result from {result_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(result_url) as response:
                    if response.status == 200:
                        with open(local_path, 'wb') as f:
                            f.write(await response.read())
                        logger.info(f"Downloaded result to {local_path}")
                        return local_path
                    else:
                        raise Exception(f"Download failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error downloading result: {e}")
            raise


# Global service instance
# Initialize with API key from environment config
from backend.config import settings

sync_segments_service = SyncSegmentsService(
    api_key=getattr(settings, 'sync_api_key', None)
)
