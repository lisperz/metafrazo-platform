"""
Callback service for notifying phraze.so of job status changes
"""

import logging
import httpx
import socket
from datetime import datetime
from typing import Optional

from backend.config import settings
from .schemas import PhrazeCallbackPayload, CallbackStatus
from .validator import PhrazeValidator

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 15]  # Exponential backoff in seconds


def _normalize_callback_url(url: str) -> str:
    """
    Normalize callback URL for the current environment.

    When running on the host (not in Docker), convert host.docker.internal
    back to localhost, since host.docker.internal is only resolvable from
    inside Docker containers.
    """
    if "host.docker.internal" not in url:
        return url

    # Check if we're running inside Docker by trying to resolve host.docker.internal
    try:
        socket.gethostbyname("host.docker.internal")
        # If successful, we're inside Docker - keep the URL as is
        return url
    except socket.gaierror:
        # Cannot resolve - we're on the host, convert to localhost
        normalized = url.replace("host.docker.internal", "localhost")
        logger.debug(f"Normalized callback URL: {url} -> {normalized}")
        return normalized


class PhrazeCallbackService:
    """Service for sending callbacks to phraze.so"""

    @staticmethod
    async def send_callback(
        callback_url: str,
        job_id: str,
        status: CallbackStatus,
        output_url: Optional[str] = None,
        processing_time_seconds: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Send callback notification to phraze.so
        Returns True if successful, False otherwise
        """
        payload = PhrazeCallbackPayload(
            job_id=job_id,
            status=status,
            output_url=output_url,
            processing_time_seconds=processing_time_seconds,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {},
            timestamp=datetime.utcnow()
        )

        # Generate signature
        payload_dict = payload.model_dump()
        payload_dict["timestamp"] = payload.timestamp.isoformat()
        signature = PhrazeValidator.generate_callback_signature(payload_dict)
        payload_dict["signature"] = signature

        # Use configured callback URL if none provided
        raw_url = callback_url or settings.phraze_callback_url
        # Normalize URL for the current environment (host vs Docker)
        target_url = _normalize_callback_url(raw_url)

        logger.info(f"Sending callback to {target_url} for job {job_id} with status {status}")

        # Try sending with retries
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        target_url,
                        json=payload_dict,
                        headers={
                            "Content-Type": "application/json",
                            "X-Editor-Signature": signature,
                            "X-Editor-Source": "metafrazo-editor"
                        }
                    )

                    if response.status_code in [200, 201, 202]:
                        logger.info(f"Callback successful for job {job_id}: {response.status_code}")
                        return True

                    logger.warning(
                        f"Callback failed for job {job_id}: {response.status_code} - {response.text}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"Callback timeout for job {job_id}, attempt {attempt + 1}/{MAX_RETRIES}")
            except httpx.RequestError as e:
                logger.warning(f"Callback request error for job {job_id}: {e}, attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                logger.error(f"Unexpected error sending callback for job {job_id}: {e}")

            # Wait before retry (except on last attempt)
            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(RETRY_DELAYS[attempt])

        logger.error(f"All callback attempts failed for job {job_id}")
        return False

    @staticmethod
    async def notify_job_started(
        callback_url: str,
        job_id: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """Notify phraze.so that job processing has started"""
        return await PhrazeCallbackService.send_callback(
            callback_url=callback_url,
            job_id=job_id,
            status=CallbackStatus.STARTED,
            metadata=metadata
        )

    @staticmethod
    async def notify_job_completed(
        callback_url: str,
        job_id: str,
        output_url: str,
        processing_time_seconds: int,
        metadata: Optional[dict] = None
    ) -> bool:
        """Notify phraze.so that job processing has completed"""
        return await PhrazeCallbackService.send_callback(
            callback_url=callback_url,
            job_id=job_id,
            status=CallbackStatus.COMPLETED,
            output_url=output_url,
            processing_time_seconds=processing_time_seconds,
            metadata=metadata
        )

    @staticmethod
    async def notify_job_failed(
        callback_url: str,
        job_id: str,
        error_code: str,
        error_message: str,
        processing_time_seconds: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Notify phraze.so that job processing has failed"""
        return await PhrazeCallbackService.send_callback(
            callback_url=callback_url,
            job_id=job_id,
            status=CallbackStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
            processing_time_seconds=processing_time_seconds,
            metadata=metadata
        )


# Error code mapping for consistent error reporting
ERROR_CODES = {
    "TOKEN_EXPIRED": "Your session has expired",
    "TOKEN_INVALID": "Invalid authentication token",
    "VIDEO_NOT_FOUND": "Video file not found in S3",
    "VIDEO_DOWNLOAD_FAILED": "Failed to download video from S3",
    "PROCESSING_FAILED": "Video processing failed",
    "SYNC_API_ERROR": "Lip-sync API error",
    "GHOSTCUT_API_ERROR": "Text removal API error",
    "S3_UPLOAD_FAILED": "Failed to upload processed video",
    "TIMEOUT": "Processing timed out",
    "UNKNOWN_ERROR": "An unexpected error occurred"
}


def get_error_message(error_code: str) -> str:
    """Get human-readable error message for error code"""
    return ERROR_CODES.get(error_code, ERROR_CODES["UNKNOWN_ERROR"])
