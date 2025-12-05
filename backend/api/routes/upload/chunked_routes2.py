from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import hashlib
import aiofiles
from typing import Optional
import uuid
from datetime import datetime, timedelta

from backend.models.database import get_database as get_db
from backend.models.user import User
from backend.auth.dependencies import get_current_user
from backend.config import settings as config_settings

def get_settings():
    return config_settings

router = APIRouter(prefix="/chunked-upload", tags=["chunked-upload"])
settings = get_settings()

# In-memory storage for upload sessions (in production, use Redis)
upload_sessions = {}

class ChunkedUploadSession:
    def __init__(self, upload_id: str, filename: str, total_size: int, chunk_size: int):
        self.upload_id = upload_id
        self.filename = filename
@router.post("/finalize/{upload_id}")
async def finalize_chunked_upload(
    upload_id: str,
    final_hash: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Finalize chunked upload by combining all chunks"""
    
    # Get upload session
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = upload_sessions[upload_id]
    
    # Check if upload is complete
    if not session.is_complete():
        raise HTTPException(
            status_code=400, 
            detail=f"Upload incomplete. Received {len(session.chunks_received)}/{session.total_chunks} chunks"
        )
    
    try:
        # Create final file path
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(session.filename)[1]
        final_filename = f"{file_id}{file_extension}"
        final_path = os.path.join(settings.upload_path, final_filename)
        
        # Combine chunks into final file
        async with aiofiles.open(final_path, 'wb') as final_file:
            for chunk_number in range(session.total_chunks):
                chunk_path = os.path.join(session.temp_dir, f"chunk_{chunk_number:06d}")
                if not os.path.exists(chunk_path):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Missing chunk {chunk_number}"
                    )
                
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    chunk_data = await chunk_file.read()
                    await final_file.write(chunk_data)
        
        # Verify final file hash if provided
        if final_hash:
            with open(final_path, 'rb') as f:
                calculated_hash = hashlib.md5(f.read()).hexdigest()
                if calculated_hash != final_hash:
                    os.remove(final_path)
                    raise HTTPException(status_code=400, detail="Final file hash verification failed")
        
        # Get final file size
        final_size = os.path.getsize(final_path)
        
        # Clean up temp files
        cleanup_upload_session(upload_id)
        
        return {
            "file_id": file_id,
            "filename": final_filename,
            "original_filename": session.filename,
            "file_path": final_path,
            "file_size": final_size,
            "upload_complete": True
        }
    
    except Exception as e:
        # Clean up on error
        cleanup_upload_session(upload_id)
        raise HTTPException(status_code=500, detail=f"Failed to finalize upload: {str(e)}")

@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of chunked upload"""
    
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = upload_sessions[upload_id]
    
    if session.is_expired():
        cleanup_upload_session(upload_id)
        raise HTTPException(status_code=410, detail="Upload session expired")
    
    return {
        "upload_id": upload_id,
        "filename": session.filename,
        "total_size": session.total_size,
        "chunks_received": len(session.chunks_received),
        "total_chunks": session.total_chunks,
        "is_complete": session.is_complete(),
        "progress": (len(session.chunks_received) / session.total_chunks) * 100,
        "missing_chunks": [i for i in range(session.total_chunks) if i not in session.chunks_received]
    }

@router.delete("/cancel/{upload_id}")
async def cancel_chunked_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel and cleanup chunked upload"""
    
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    cleanup_upload_session(upload_id)
    
    return {"message": "Upload cancelled and cleaned up"}

def cleanup_upload_session(upload_id: str):
    """Clean up upload session and temp files"""
    if upload_id in upload_sessions:
        session = upload_sessions[upload_id]
        
        # Remove temp directory and all chunks
        import shutil
        if os.path.exists(session.temp_dir):
            shutil.rmtree(session.temp_dir)
        
        # Remove from memory
        del upload_sessions[upload_id]

@router.post("/cleanup-expired")
async def cleanup_expired_uploads():
    """Clean up expired upload sessions (admin endpoint)"""
    expired_uploads = []
    
    for upload_id, session in list(upload_sessions.items()):
        if session.is_expired():
            cleanup_upload_session(upload_id)
            expired_uploads.append(upload_id)
    
    return {
        "cleaned_up": len(expired_uploads),
        "upload_ids": expired_uploads
    }