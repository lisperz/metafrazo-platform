"""
Sync.so API integration for segment-based lip-sync processing
Real implementation using Sync.so segments API documentation
"""

import logging
import aiohttp
import json
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def build_bounding_boxes(
    video_fps: float,
    total_frames: int,
    segments: List[dict],
    video_width: int,
    video_height: int
) -> Optional[List]:
    """
    Build per-frame bounding boxes array from segments with speaker boxes.

    This enables per-segment speaker selection by providing a fixed bounding box
    for each frame within a segment. Frames outside segments or segments without
    speaker boxes get null (auto-detect).

    Args:
        video_fps: Video frame rate (frames per second)
        total_frames: Total number of frames in the video
        segments: List of segment configurations with optional speakerBox
        video_width: Video width in pixels
        video_height: Video height in pixels

    Returns:
        List of bounding boxes [x1, y1, x2, y2] or null for each frame,
        or None if no segments have speaker boxes (use auto-detect for all)

    Example:
        segments = [
            {"startTime": 2.0, "endTime": 10.0, "speakerBox": {"x1": 0.3, "y1": 0.2, "x2": 0.7, "y2": 0.8}},
            {"startTime": 15.0, "endTime": 20.0}  # No speaker box - auto-detect
        ]

        Result: [null, null, ..., [x1,y1,x2,y2], [x1,y1,x2,y2], ..., null, ...]
    """
    # Check if any segment has a speaker box
    has_any_speaker_box = any(
        seg.get("speakerBox") and seg["speakerBox"].get("method") == "manual"
        for seg in segments
    )

    if not has_any_speaker_box:
        logger.info("No segments have manual speaker boxes - using auto-detect for all")
        return None

    # Initialize all frames to null (auto-detect)
    boxes = [None] * total_frames

    for seg in segments:
        speaker_box = seg.get("speakerBox")

        # Skip segments without manual speaker box
        if not speaker_box or speaker_box.get("method") != "manual":
            continue

        # Calculate frame range for this segment
        start_frame = int(seg["startTime"] * video_fps)
        end_frame = min(int(seg["endTime"] * video_fps), total_frames - 1)

        # Convert normalized coordinates (0-1) to pixel coordinates
        # Sync.so expects [x1, y1, x2, y2] in pixels
        x1 = int(speaker_box["x1"] * video_width)
        y1 = int(speaker_box["y1"] * video_height)
        x2 = int(speaker_box["x2"] * video_width)
        y2 = int(speaker_box["y2"] * video_height)

        box = [x1, y1, x2, y2]

        logger.info(
            f"Segment {seg.get('startTime')}-{seg.get('endTime')}: "
            f"frames {start_frame}-{end_frame}, box={box}"
        )

        # Set the same box for all frames in this segment
        for frame in range(start_frame, end_frame + 1):
            if frame < total_frames:
                boxes[frame] = box

    # Count non-null boxes for logging
    non_null_count = sum(1 for b in boxes if b is not None)
    logger.info(
        f"Built bounding_boxes array: {total_frames} frames, "
        f"{non_null_count} with speaker box, {total_frames - non_null_count} auto-detect"
    )

    return boxes


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
        audio_url_mapping: Dict[str, str],
        video_metadata: Optional[dict] = None
    ) -> dict:
        """
        Create a lip-sync generation with multiple segments

        API Reference: https://docs.sync.so/developer-guides/segments

        Args:
            video_url: S3 URL of the video file
            segments: List of segment configurations from frontend
            audio_url_mapping: Dict mapping refId -> S3 URL for audio files
            video_metadata: Optional dict with fps, total_frames, width, height
                           for building bounding_boxes array

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
                "speakerBox": {        # Optional speaker bounding box
                    "x1": 0.3, "y1": 0.2,
                    "x2": 0.7, "y2": 0.8,
                    "method": "manual"
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

            # Build options with sync_mode
            options = {
                "sync_mode": "remap"  # Remap works correctly when audio crop times match segment times
            }

            # Build bounding_boxes array if video metadata is provided and segments have speaker boxes
            if video_metadata:
                fps = video_metadata.get("fps", 30)
                total_frames = video_metadata.get("total_frames")
                width = video_metadata.get("width")
                height = video_metadata.get("height")

                if total_frames and width and height:
                    bounding_boxes = build_bounding_boxes(
                        video_fps=fps,
                        total_frames=total_frames,
                        segments=segments,
                        video_width=width,
                        video_height=height
                    )

                    if bounding_boxes:
                        options["active_speaker_detection"] = {
                            "bounding_boxes": bounding_boxes
                        }
                        logger.info(f"Added bounding_boxes to options ({len(bounding_boxes)} frames)")
                else:
                    logger.warning(
                        f"Incomplete video metadata for bounding boxes: "
                        f"fps={fps}, frames={total_frames}, size={width}x{height}"
                    )

            # Build final API request payload
            payload = {
                "model": "lipsync-2-pro",  # Pro model for higher quality lip-sync
                "input": input_array,
                "segments": segments_array,
                "options": options
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
