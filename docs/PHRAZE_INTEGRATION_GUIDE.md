# Phraze.so Embedded Editor Integration Guide

This document provides comprehensive integration specifications for embedding the Metafrazo video editor into Phraze.so. It covers JWT authentication, database schema, callback handling, and security considerations.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Database Schema (Phraze.so Side)](#3-database-schema-phrazeso-side)
4. [JWT Token Specification](#4-jwt-token-specification)
5. [Editor URL Construction](#5-editor-url-construction)
6. [Callback Handling](#6-callback-handling)
7. [Error Handling](#7-error-handling)
8. [Security Considerations](#8-security-considerations)
9. [Code Examples](#9-code-examples)

---

## 1. Overview

The Metafrazo embedded editor allows Phraze.so users to perform:
- **Lip-sync processing**: Replace audio in video segments with AI-generated lip-sync
- **Text removal (inpainting)**: Remove text/watermarks from video using AI
- **Combined processing**: Both lip-sync and text removal in a single workflow

### Integration Flow

```
┌─────────────┐     JWT Token      ┌─────────────────┐     Callback      ┌─────────────┐
│  Phraze.so  │ ──────────────────>│ Metafrazo Editor│ ─────────────────>│  Phraze.so  │
│  (Frontend) │                    │   (Embedded)    │                   │  (Backend)  │
└─────────────┘                    └─────────────────┘                   └─────────────┘
      │                                    │                                    │
      │ 1. User clicks "Edit Video"        │                                    │
      │ 2. Generate JWT token              │                                    │
      │ 3. Redirect to editor URL          │                                    │
      │                                    │ 4. User edits video                │
      │                                    │ 5. Submit for processing           │
      │                                    │                                    │
      │                                    │ 6. Processing completes            │
      │                                    │───────────────────────────────────>│
      │                                    │    POST callback with result       │
      │<───────────────────────────────────│                                    │
      │        7. User returns to Phraze.so                                     │
```

---

## 2. Architecture

### Components

| Component | Owner | Description |
|-----------|-------|-------------|
| JWT Generation | Phraze.so | Generate signed JWT tokens with video info |
| Editor Frontend | Metafrazo | React-based video editor UI |
| Processing Backend | Metafrazo | FastAPI backend for video processing |
| Callback Endpoint | Phraze.so | HTTP endpoint to receive job results |
| S3 Storage | Shared | Video storage (can use Phraze.so's bucket) |

### Subscription Tiers

| Tier | Editor Type | Features |
|------|-------------|----------|
| `free` | Basic Editor | Text removal only |
| `normal` | Basic Editor | Text removal only |
| `pro` | Pro Editor | Full lip-sync + text removal |
| `enterprise` | Pro Editor | Full lip-sync + text removal + priority |

---

## 3. Database Schema (Phraze.so Side)

### Required Tables

```sql
-- Editing jobs table
CREATE TABLE editor_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),

    -- Video information
    video_url TEXT NOT NULL,                    -- S3 URL of source video
    video_duration_seconds FLOAT,               -- Video duration for UI

    -- Processing configuration (optional, for re-editing)
    processing_type VARCHAR(20) DEFAULT 'text_removal', -- 'lip_sync', 'text_removal', 'both'
    segments_data JSONB,                        -- Lip-sync segments configuration
    effects_data JSONB,                         -- Erasure/protection areas

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending',       -- 'pending', 'editing', 'processing', 'completed', 'failed'
    output_url TEXT,                            -- S3 URL of processed video
    error_code VARCHAR(50),                     -- Error code if failed
    error_message TEXT,                         -- Error details if failed

    -- Timing
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,                       -- When processing started
    completed_at TIMESTAMP,                     -- When processing finished
    processing_time_seconds INT,                -- Total processing time

    -- Metadata
    callback_received_at TIMESTAMP,             -- When callback was received
    internal_job_id VARCHAR(100),               -- Metafrazo internal job ID
    sync_generation_id VARCHAR(100),            -- Sync.so generation ID (for debugging)

    CONSTRAINT valid_status CHECK (status IN ('pending', 'editing', 'processing', 'completed', 'failed'))
);

-- Index for common queries
CREATE INDEX idx_editor_jobs_user ON editor_jobs(user_id);
CREATE INDEX idx_editor_jobs_status ON editor_jobs(status);
CREATE INDEX idx_editor_jobs_created ON editor_jobs(created_at DESC);

-- JWT signing keys (for RS256)
CREATE TABLE jwt_signing_keys (
    id SERIAL PRIMARY KEY,
    key_id VARCHAR(50) UNIQUE NOT NULL,         -- Key identifier (kid)
    private_key TEXT NOT NULL,                  -- RSA private key (PEM format)
    public_key TEXT NOT NULL,                   -- RSA public key (PEM format)
    algorithm VARCHAR(10) DEFAULT 'RS256',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    rotated_at TIMESTAMP
);

-- Callback verification secrets
CREATE TABLE callback_secrets (
    id SERIAL PRIMARY KEY,
    secret_key VARCHAR(64) NOT NULL,            -- HMAC secret for callback verification
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Segments Data Schema (JSONB)

For lip-sync processing, `segments_data` should contain:

```json
[
  {
    "startTime": 0.0,
    "endTime": 5.5,
    "audioInput": {
      "refId": "audio-uuid-1",
      "url": "https://s3.amazonaws.com/bucket/audio1.mp3",
      "startTime": 0.0,
      "endTime": 5.5
    }
  },
  {
    "startTime": 10.0,
    "endTime": 15.0,
    "audioInput": {
      "refId": "audio-uuid-2",
      "url": "https://s3.amazonaws.com/bucket/audio2.mp3",
      "startTime": 0.0,
      "endTime": 5.0
    }
  }
]
```

### Effects Data Schema (JSONB)

For text removal, `effects_data` should contain:

```json
[
  {
    "type": "erasure",
    "startTime": 0.0,
    "endTime": 30.0,
    "region": {
      "x": 0.1,
      "y": 0.8,
      "width": 0.8,
      "height": 0.15
    }
  },
  {
    "type": "protection",
    "startTime": 5.0,
    "endTime": 10.0,
    "region": {
      "x": 0.4,
      "y": 0.4,
      "width": 0.2,
      "height": 0.2
    }
  }
]
```

**Effect Types:**
- `erasure`: Area to remove (text/watermark will be inpainted)
- `protection`: Area to preserve (won't be affected by full-screen removal)

**Region Coordinates:**
- All values are normalized (0.0 to 1.0)
- `x`, `y`: Top-left corner position
- `width`, `height`: Size relative to video dimensions

---

## 4. JWT Token Specification

### Token Structure

The JWT token uses **RS256** (RSA Signature with SHA-256) algorithm.

```
Header:
{
  "alg": "RS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "user-uuid",              // Required: Phraze.so user ID
  "job_id": "job-uuid",            // Required: Phraze.so job ID
  "video_url": "https://...",      // Required: S3 URL of video to edit
  "callback_url": "https://...",   // Required: URL to receive completion callback
  "permissions": ["edit", "process"], // Required: Granted permissions
  "subscription_tier": "pro",      // Required: "free", "normal", "pro", "enterprise"
  "iat": 1703123456,               // Required: Issued at (Unix timestamp)
  "exp": 1703127056                // Required: Expiration (Unix timestamp)
}
```

### Field Specifications

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sub` | string | Yes | Phraze.so user ID (will be used for S3 path organization) |
| `job_id` | string | Yes | Unique job identifier from Phraze.so |
| `video_url` | string | Yes | Public S3 URL of the source video |
| `callback_url` | string | Yes | HTTPS endpoint to receive job callbacks |
| `permissions` | string[] | Yes | Always `["edit", "process"]` |
| `subscription_tier` | string | Yes | User's subscription level |
| `iat` | integer | Yes | Token issue time (Unix timestamp) |
| `exp` | integer | Yes | Token expiration (Unix timestamp) |

### Token Expiration

- **Recommended**: 1-4 hours
- **Maximum**: 24 hours
- Token is validated on each API request

### Generating RSA Key Pair

```bash
# Generate RSA private key (2048-bit)
openssl genrsa -out phraze_private.pem 2048

# Extract public key
openssl rsa -in phraze_private.pem -pubout -out phraze_public.pem
```

**Important**:
- Store private key securely on Phraze.so servers only
- Share public key with Metafrazo for token verification

---

## 5. Editor URL Construction

### URL Format

```
https://editor.metafrazo.com/editor/embedded?token={JWT_TOKEN}
```

### Example Implementation (Python)

```python
import jwt
from datetime import datetime, timedelta
from urllib.parse import urlencode

def generate_editor_url(
    user_id: str,
    job_id: str,
    video_url: str,
    callback_url: str,
    subscription_tier: str = "normal",
    expires_in_hours: int = 1
) -> str:
    """Generate signed URL to embedded editor"""

    # Load your RSA private key
    with open('phraze_private.pem', 'r') as f:
        private_key = f.read()

    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "job_id": job_id,
        "video_url": video_url,
        "callback_url": callback_url,
        "permissions": ["edit", "process"],
        "subscription_tier": subscription_tier,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_in_hours)).timestamp())
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")

    return f"https://editor.metafrazo.com/editor/embedded?token={token}"
```

---

## 6. Callback Handling

### Callback Request Format

When processing completes (success or failure), Metafrazo sends an HTTP POST to your `callback_url`:

```http
POST /api/editor/callback HTTP/1.1
Host: api.phraze.so
Content-Type: application/json
X-Editor-Signature: {HMAC_SIGNATURE}
X-Editor-Source: metafrazo-editor

{
  "job_id": "job-uuid-from-token",
  "status": "completed",
  "output_url": "https://s3.amazonaws.com/metafrazo/output/processed.mp4",
  "processing_time_seconds": 245,
  "metadata": {
    "internal_job_id": "uuid-internal",
    "sync_generation_id": "sync-so-id"
  },
  "timestamp": "2024-12-21T18:30:00.000Z",
  "signature": "hmac-sha256-signature"
}
```

### Callback Status Values

| Status | Description |
|--------|-------------|
| `started` | Job processing has begun |
| `processing` | Job is actively being processed (optional) |
| `completed` | Processing finished successfully |
| `failed` | Processing failed |

### Success Callback Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job ID from the JWT token |
| `status` | string | `"completed"` |
| `output_url` | string | S3 URL of processed video |
| `processing_time_seconds` | integer | Total processing time |
| `metadata.internal_job_id` | string | Metafrazo internal job ID |
| `metadata.sync_generation_id` | string | Sync.so generation ID (if lip-sync was used) |
| `timestamp` | string | ISO 8601 timestamp |
| `signature` | string | HMAC-SHA256 signature for verification |

### Failure Callback Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job ID from the JWT token |
| `status` | string | `"failed"` |
| `error_code` | string | Error code (see Error Codes section) |
| `error_message` | string | Human-readable error description |
| `processing_time_seconds` | integer | Time elapsed before failure |
| `metadata.internal_job_id` | string | Metafrazo internal job ID |
| `timestamp` | string | ISO 8601 timestamp |
| `signature` | string | HMAC-SHA256 signature |

### Callback Verification

Verify callback authenticity using HMAC-SHA256:

```python
import hmac
import hashlib

def verify_callback_signature(payload: dict, received_signature: str, secret: str) -> bool:
    """Verify callback signature"""
    message_parts = [
        payload.get("job_id", ""),
        payload.get("status", ""),
        payload.get("output_url", ""),
        payload.get("timestamp", "")
    ]
    message = "|".join(str(p) for p in message_parts)

    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)
```

### Callback Endpoint Implementation

```python
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI()

class EditorCallback(BaseModel):
    job_id: str
    status: str  # "started", "processing", "completed", "failed"
    output_url: Optional[str] = None
    processing_time_seconds: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None
    timestamp: str
    signature: str

@app.post("/api/editor/callback")
async def handle_editor_callback(
    payload: EditorCallback,
    x_editor_signature: str = Header(...),
    x_editor_source: str = Header(...)
):
    # Verify source
    if x_editor_source != "metafrazo-editor":
        raise HTTPException(status_code=403, detail="Invalid source")

    # Verify signature
    if not verify_callback_signature(payload.dict(), payload.signature, CALLBACK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Find job in database
    job = await db.fetch_one(
        "SELECT * FROM editor_jobs WHERE id = :id",
        {"id": uuid.UUID(payload.job_id)}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job based on status
    if payload.status == "completed":
        await db.execute("""
            UPDATE editor_jobs SET
                status = 'completed',
                output_url = :output_url,
                processing_time_seconds = :processing_time,
                completed_at = NOW(),
                callback_received_at = NOW(),
                internal_job_id = :internal_job_id
            WHERE id = :id
        """, {
            "id": payload.job_id,
            "output_url": payload.output_url,
            "processing_time": payload.processing_time_seconds,
            "internal_job_id": payload.metadata.get("internal_job_id")
        })

        # Notify user (email, push notification, etc.)
        await notify_user_job_complete(job["user_id"], payload.output_url)

    elif payload.status == "failed":
        await db.execute("""
            UPDATE editor_jobs SET
                status = 'failed',
                error_code = :error_code,
                error_message = :error_message,
                completed_at = NOW(),
                callback_received_at = NOW()
            WHERE id = :id
        """, {
            "id": payload.job_id,
            "error_code": payload.error_code,
            "error_message": payload.error_message
        })

        # Notify user of failure
        await notify_user_job_failed(job["user_id"], payload.error_message)

    return {"received": True, "job_id": payload.job_id}
```

---

## 7. Error Handling //// !!! NO

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TOKEN_MISSING` | 401 | No JWT token provided |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `TOKEN_INVALID` | 401 | JWT signature verification failed |
| `TOKEN_MALFORMED` | 400 | JWT payload missing required fields |
| `VIDEO_NOT_FOUND` | 404 | Source video not accessible |
| `VIDEO_DOWNLOAD_FAILED` | 500 | Failed to download source video |
| `PROCESSING_FAILED` | 500 | General processing failure |
| `SYNC_FAILED` | 500 | Lip-sync API error |
| `GHOSTCUT_FAILED` | 500 | Text removal API error |
| `S3_UPLOAD_FAILED` | 500 | Failed to upload processed video |
| `TIMEOUT` | 504 | Processing timed out |

### Error Response Format

```json
{
  "error_code": "TOKEN_EXPIRED",
  "message": "Your session has expired. Please return to phraze.so to continue.",
  "redirect_url": "https://phraze.so/editor",
  "job_id": "job-uuid",
  "timestamp": "2024-12-21T18:30:00.000Z"
}
```

### Handling Token Expiration in Frontend

```javascript
// In embedded editor, handle token errors
window.addEventListener('message', (event) => {
  if (event.data.type === 'EDITOR_ERROR') {
    if (event.data.error_code === 'TOKEN_EXPIRED') {
      // Redirect back to Phraze.so
      window.location.href = event.data.redirect_url;
    }
  }
});
```

---

## 8. Security Considerations

### Key Management

1. **RSA Key Rotation**: Rotate signing keys every 90 days
2. **Key Storage**: Store private keys in secure vault (AWS Secrets Manager, HashiCorp Vault)
3. **Public Key Distribution**: Share public key with Metafrazo via secure channel

### Callback Security

1. **HTTPS Only**: Callback URL must use HTTPS
2. **Signature Verification**: Always verify HMAC signature
3. **IP Whitelisting**: Optionally whitelist Metafrazo's IP addresses
4. **Rate Limiting**: Implement rate limiting on callback endpoint

### Token Security

1. **Short Expiration**: Use 1-4 hour expiration
2. **One-Time Use**: Consider invalidating tokens after first use
3. **Secure Transmission**: Always use HTTPS
4. **No Sensitive Data**: Don't include sensitive user data in JWT

### S3 URL Security

1. **Signed URLs**: Use pre-signed S3 URLs with short expiration
2. **Domain Validation**: Validate S3 domains in token
3. **Access Logging**: Enable S3 access logging

---

## 9. Code Examples

### Complete Integration Example (Node.js/TypeScript)

```typescript
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';

interface EditorJobConfig {   !!!!(no)
  userId: string;
  videoUrl: string;
  subscriptionTier: 'free' | 'normal' | 'pro' | 'enterprise';
}

interface EditorCallback {  
  jobId: string;
  status: 'started' | 'processing' | 'completed' | 'failed';
  outputUrl?: string;
  processingTimeSeconds?: number;
  errorCode?: string;
  errorMessage?: string;
  metadata?: Record<string, string>;
  timestamp: string;
  signature: string;
}

class EditorIntegration {
  private privateKey: string;
  private callbackSecret: string;
  private callbackUrl: string;
  private editorBaseUrl: string;

  constructor(config: {
    privateKeyPath: string;
    callbackSecret: string;
    callbackUrl: string;
    editorBaseUrl: string;
  }) {
    this.privateKey = fs.readFileSync(config.privateKeyPath, 'utf8');
    this.callbackSecret = config.callbackSecret;
    this.callbackUrl = config.callbackUrl;
    this.editorBaseUrl = config.editorBaseUrl;
  }

  /**
   * Create a new editing job and generate editor URL
   */
  async createEditorSession(config: EditorJobConfig): Promise<{
    jobId: string;
    editorUrl: string;
  }> {
    const jobId = uuidv4();

    // Save job to database
    await db.query(`
      INSERT INTO editor_jobs (id, user_id, video_url, status)
      VALUES ($1, $2, $3, 'pending')
    `, [jobId, config.userId, config.videoUrl]);

    // Generate JWT token
    const token = this.generateToken(jobId, config);

    // Construct editor URL
    const editorUrl = `${this.editorBaseUrl}/editor/embedded?token=${token}`;

    return { jobId, editorUrl };
  }

  /**
   * Generate signed JWT token
   */
  private generateToken(jobId: string, config: EditorJobConfig): string {
    const now = Math.floor(Date.now() / 1000);
    const expiresIn = 4 * 60 * 60; // 4 hours

    const payload = {
      sub: config.userId,
      job_id: jobId,
      video_url: config.videoUrl,
      callback_url: this.callbackUrl,
      permissions: ['edit', 'process'],
      subscription_tier: config.subscriptionTier,
      iat: now,
      exp: now + expiresIn,
    };

    return jwt.sign(payload, this.privateKey, { algorithm: 'RS256' });
  }

  /**
   * Verify callback signature
   */
  verifyCallbackSignature(payload: EditorCallback): boolean {
    const message = [
      payload.jobId,
      payload.status,
      payload.outputUrl || '',
      payload.timestamp,
    ].join('|');

    const expectedSignature = crypto
      .createHmac('sha256', this.callbackSecret)
      .update(message)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(expectedSignature),
      Buffer.from(payload.signature)
    );
  }

  /**
   * Handle incoming callback
   */
  async handleCallback(payload: EditorCallback): Promise<void> {
    // Verify signature
    if (!this.verifyCallbackSignature(payload)) {
      throw new Error('Invalid callback signature');
    }

    // Update job in database
    if (payload.status === 'completed') {
      await db.query(`
        UPDATE editor_jobs SET
          status = 'completed',
          output_url = $1,
          processing_time_seconds = $2,
          completed_at = NOW(),
          internal_job_id = $3
        WHERE id = $4
      `, [
        payload.outputUrl,
        payload.processingTimeSeconds,
        payload.metadata?.internal_job_id,
        payload.jobId,
      ]);
    } else if (payload.status === 'failed') {
      await db.query(`
        UPDATE editor_jobs SET
          status = 'failed',
          error_code = $1,
          error_message = $2,
          completed_at = NOW()
        WHERE id = $3
      `, [
        payload.errorCode,
        payload.errorMessage,
        payload.jobId,
      ]);
    }
  }
}

// Usage
const editor = new EditorIntegration({
  privateKeyPath: './keys/phraze_private.pem',
  callbackSecret: process.env.EDITOR_CALLBACK_SECRET!,
  callbackUrl: 'https://api.phraze.so/api/editor/callback',
  editorBaseUrl: 'https://editor.metafrazo.com',
});

// Create editing session
const { jobId, editorUrl } = await editor.createEditorSession({
  userId: 'user-123',
  videoUrl: 'https://s3.amazonaws.com/phraze/videos/source.mp4',
  subscriptionTier: 'pro',
});

// Redirect user to editor
res.redirect(editorUrl);
```

---

## Configuration Checklist

Before going live, ensure:

- [ ] RSA key pair generated and securely stored
- [ ] Public key shared with Metafrazo team
- [ ] Callback endpoint implemented and accessible via HTTPS
- [ ] HMAC callback secret configured on both sides
- [ ] Database tables created
- [ ] Error handling implemented for all error codes
- [ ] User notification system connected to callbacks
- [ ] Logging and monitoring set up
- [ ] S3 bucket CORS configured (if using Phraze.so's bucket)

---

## Support

For integration support, contact:
- Email: integration@metafrazo.com
- Documentation: https://docs.metafrazo.com/embedded

---

*Last updated: December 21, 2024*

Have sent to Harshit on Dec 21
