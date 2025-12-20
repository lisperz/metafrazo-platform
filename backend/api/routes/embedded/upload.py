"""
Embedded editor file upload endpoints for phraze.so integration
Handles audio file uploads to S3 for embedded processing
"""

import uuid
import logging
import tempfile
import os
from typing import List

from fastapi import APIRouter, Request, Query, File, UploadFile, HTTPException, status

from backend.config import settings
from backend.auth.phraze import PhrazeValidator, ErrorResponse
from backend.services.s3 import S3Service

logger = logging.getLogger(__name__)

router = APIRouter()


class AudioUploadResponse:
    """Response model for audio upload"""
    def __init__(self, ref_id: str, url: str, filename: str, file_size: int):
        self.ref_id = ref_id
        self.url = url
        self.filename = filename
        self.file_size = file_size


@router.post("/upload-audio")
async def upload_audio_file(
    request: Request,
    token: str = Query(..., description="JWT token from phraze.so"),
    file: UploadFile = File(..., description="Audio file to upload"),
    ref_id: str = Query(None, description="Optional reference ID for the audio file")
):
    """
    Upload an audio file to S3 for embedded processing.
    Returns the S3 URL that can be used in segments.
    """
    try:
        # Validate token
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        # Generate ref_id if not provided
        if not ref_id:
            ref_id = f"audio-{uuid.uuid4().hex[:8]}"

        # Validate file type
        allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav',
                        'audio/m4a', 'audio/mp4', 'audio/aac']
        if file.content_type and file.content_type not in allowed_types:
            # Check file extension as fallback
            filename_lower = file.filename.lower() if file.filename else ""
            valid_extensions = ['.mp3', '.wav', '.m4a', '.aac']
            if not any(filename_lower.endswith(ext) for ext in valid_extensions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code="INVALID_FILE_TYPE",
                        message=f"Invalid file type. Allowed: MP3, WAV, M4A, AAC"
                    ).model_dump()
                )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size (max 100MB)
        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="FILE_TOO_LARGE",
                    message=f"File too large. Maximum size: 100MB"
                ).model_dump()
            )

        # Generate S3 key
        user_id = token_payload.user_id or "embedded"
        job_id = token_payload.job_id or "unknown"
        file_ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'mp3'
        s3_key = f"embedded/{user_id}/{job_id}/audio/{ref_id}.{file_ext}"

        logger.info(f"Uploading audio file for embedded job: {s3_key}, size={file_size}")

        # Save to temp file and upload to S3
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            s3_service = S3Service()
            s3_url = s3_service.upload_video_and_get_url(temp_file_path, s3_key)

            if not s3_url:
                raise Exception("Failed to upload to S3")

            logger.info(f"Audio uploaded successfully: {s3_url[:60]}...")
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        return {
            "ref_id": ref_id,
            "url": s3_url,
            "filename": file.filename,
            "file_size": file_size,
            "message": "Audio file uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="UPLOAD_FAILED",
                message=f"Failed to upload audio file: {str(e)}"
            ).model_dump()
        )


@router.post("/upload-audio-batch")
async def upload_audio_files_batch(
    request: Request,
    token: str = Query(..., description="JWT token from phraze.so"),
    files: List[UploadFile] = File(..., description="Audio files to upload"),
):
    """
    Upload multiple audio files in a single request.
    Returns array of S3 URLs with their reference IDs.
    """
    try:
        # Validate token
        token_payload = await PhrazeValidator.validate_embedded_request(request, token)

        results = []
        errors = []

        for idx, file in enumerate(files):
            try:
                # Generate ref_id
                ref_id = f"audio-{uuid.uuid4().hex[:8]}"

                # Read file content
                content = await file.read()
                file_size = len(content)

                # Check file size (max 100MB per file)
                max_size = 100 * 1024 * 1024
                if file_size > max_size:
                    errors.append({
                        "filename": file.filename,
                        "error": "File too large (max 100MB)"
                    })
                    continue

                # Generate S3 key
                user_id = token_payload.user_id or "embedded"
                job_id = token_payload.job_id or "unknown"
                file_ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'mp3'
                s3_key = f"embedded/{user_id}/{job_id}/audio/{ref_id}.{file_ext}"

                # Save to temp file and upload to S3
                temp_file_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp_file:
                        temp_file.write(content)
                        temp_file_path = temp_file.name

                    s3_service = S3Service()
                    s3_url = s3_service.upload_video_and_get_url(temp_file_path, s3_key)

                    if not s3_url:
                        raise Exception("Failed to upload to S3")
                finally:
                    # Clean up temp file
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

                results.append({
                    "ref_id": ref_id,
                    "url": s3_url,
                    "filename": file.filename,
                    "file_size": file_size
                })

                logger.info(f"Batch upload: File {idx+1}/{len(files)} uploaded: {file.filename}")

            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        return {
            "uploaded": results,
            "errors": errors,
            "total_uploaded": len(results),
            "total_errors": len(errors)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="BATCH_UPLOAD_FAILED",
                message=f"Failed to upload audio files: {str(e)}"
            ).model_dump()
        )
