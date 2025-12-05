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
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.chunks_received = set()
        self.total_chunks = (total_size + chunk_size - 1) // chunk_size
        self.temp_dir = os.path.join(settings.upload_path, "temp", upload_id)
        self.created_at = datetime.utcnow()
        
        # Create temp directory
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def is_complete(self) -> bool:
        return len(self.chunks_received) == self.total_chunks
    
    def is_expired(self) -> bool:
        return datetime.utcnow() - self.created_at > timedelta(hours=24)

@router.post("/initialize")
async def initialize_chunked_upload(
    filename: str = Form(...),
    total_size: int = Form(...),
    chunk_size: int = Form(default=1024*1024),  # 1MB default
    content_hash: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize a chunked upload session"""

    # Get user's subscription tier name
    tier_name = "free"
    if current_user.subscription_tier:
        tier_name = current_user.subscription_tier.name

    # Validate file size limits based on user plan
    max_file_size = {
        'free': 100 * 1024 * 1024,      # 100MB
        'pro': 500 * 1024 * 1024,       # 500MB
        'enterprise': 2 * 1024 * 1024 * 1024  # 2GB
    }.get(tier_name, 100 * 1024 * 1024)

    if total_size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds limit for {tier_name} plan"
        )
    
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.wmv'}
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported"
        )
    
    # Generate upload ID
    upload_id = str(uuid.uuid4())
    
    # Create upload session
    session = ChunkedUploadSession(upload_id, filename, total_size, chunk_size)
    upload_sessions[upload_id] = session
    
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": session.total_chunks,
        "expires_at": (session.created_at + timedelta(hours=24)).isoformat()
    }

@router.post("/chunk/{upload_id}")
async def upload_chunk(
    upload_id: str,
    chunk_number: int = Form(...),
    chunk: UploadFile = File(...),
    chunk_hash: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Upload a single chunk"""
    
    # Get upload session
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = upload_sessions[upload_id]
    
    # Check if session is expired
    if session.is_expired():
        # Clean up expired session
        cleanup_upload_session(upload_id)
        raise HTTPException(status_code=410, detail="Upload session expired")
    
    # Validate chunk number
    if chunk_number < 0 or chunk_number >= session.total_chunks:
        raise HTTPException(status_code=400, detail="Invalid chunk number")
    
    # Check if chunk already received
    if chunk_number in session.chunks_received:
        return {"message": "Chunk already received", "chunk_number": chunk_number}
    
    # Read chunk data
    chunk_data = await chunk.read()
    
    # Verify chunk hash if provided
    if chunk_hash:
        calculated_hash = hashlib.md5(chunk_data).hexdigest()
        if calculated_hash != chunk_hash:
            raise HTTPException(status_code=400, detail="Chunk hash verification failed")
    
    # Save chunk to temp file
    chunk_path = os.path.join(session.temp_dir, f"chunk_{chunk_number:06d}")
    async with aiofiles.open(chunk_path, 'wb') as f:
        await f.write(chunk_data)
    
    # Mark chunk as received
    session.chunks_received.add(chunk_number)
    
    # Check if upload is complete
    is_complete = session.is_complete()
    
    return {
        "chunk_number": chunk_number,
        "chunks_received": len(session.chunks_received),
        "total_chunks": session.total_chunks,
        "is_complete": is_complete,
        "progress": (len(session.chunks_received) / session.total_chunks) * 100
    }

