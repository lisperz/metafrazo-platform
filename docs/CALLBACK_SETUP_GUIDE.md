# Callback Setup Guide for Phraze.so Integration

## Current Status

✅ **Callback functionality is fully implemented** in MetaFrazo backend.

When a video job completes, MetaFrazo sends an HTTP POST callback to the URL specified in the JWT token.

## Callback Flow

```
1. User submits job via embedded editor
   ↓
2. MetaFrazo sends "started" callback
   POST {callback_url}
   {
     "job_id": "phraze-job-uuid",
     "status": "started",
     "timestamp": "..."
   }
   ↓
3. MetaFrazo processes video (lip-sync/text removal)
   ↓
4. MetaFrazo sends "completed" callback
   POST {callback_url}
   {
     "job_id": "phraze-job-uuid",
     "status": "completed",
     "output_url": "https://s3.amazonaws.com/...",
     "processing_time_seconds": 120,
     "metadata": {...}
   }
```

## The Problem

Your current JWT token has:
```json
{
  "callback_url": "http://localhost:3000/api/open/editor-jobs"
}
```

**This won't work** because:
- MetaFrazo backend runs on **Railway** (cloud server)
- Railway cannot reach `localhost:3000` (your local machine)
- Callbacks are being sent but fail to connect

## Solutions

### Option 1: Use ngrok (Easiest for Local Development)

1. Install ngrok: `brew install ngrok` (macOS) or download from https://ngrok.com

2. Expose your local Phraze.so backend:
   ```bash
   ngrok http 3000
   ```

3. Copy the public URL (e.g., `https://abc123.ngrok.io`)

4. Update your JWT token generation to use the ngrok URL:
   ```python
   # In your JWT generation script
   callback_url = "https://abc123.ngrok.io/api/open/editor-jobs"
   ```

5. Generate a new JWT token and test again

### Option 2: Deploy Phraze.so Backend to Railway

1. Create a new Railway service for Phraze.so backend

2. Deploy your Phraze.so backend to Railway

3. Use the Railway URL in your JWT tokens:
   ```python
   callback_url = "https://phraze-backend-production.up.railway.app/api/open/editor-jobs"
   ```

### Option 3: Use Webhook.site for Testing

1. Go to https://webhook.site (no signup needed)

2. Copy your unique URL (e.g., `https://webhook.site/abc-123`)

3. Use this URL in your JWT token:
   ```python
   callback_url = "https://webhook.site/abc-123"
   ```

4. Submit a video job

5. Check webhook.site to see the callback payload

6. Verify the callback format, then implement the same endpoint in Phraze.so

## Callback Endpoint Implementation (Phraze.so Side)

You need to implement an endpoint in your Phraze.so backend to receive callbacks:

### Express.js Example:

```javascript
// POST /api/open/editor-jobs
app.post('/api/open/editor-jobs', async (req, res) => {
  const { job_id, status, output_url, processing_time_seconds, metadata, signature } = req.body;

  // 1. Verify signature (optional but recommended)
  const isValid = verifyCallbackSignature(req.body, signature);
  if (!isValid) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // 2. Find the editor job in your database
  const editorJob = await EditorJob.findOne({ where: { id: job_id } });
  if (!editorJob) {
    return res.status(404).json({ error: 'Job not found' });
  }

  // 3. Update the job status
  if (status === 'completed') {
    editorJob.status = 'completed';
    editorJob.outputUrl = output_url;
    editorJob.processingTime = processing_time_seconds;
    editorJob.completedAt = new Date();
  } else if (status === 'failed') {
    editorJob.status = 'failed';
    editorJob.errorMessage = req.body.error_message;
  } else if (status === 'started') {
    editorJob.status = 'processing';
    editorJob.startedAt = new Date();
  }

  await editorJob.save();

  // 4. Return success response
  res.status(200).json({ success: true });
});
```

### Python/FastAPI Example:

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()

class CallbackPayload(BaseModel):
    job_id: str
    status: str  # "started", "completed", "failed"
    output_url: Optional[str] = None
    processing_time_seconds: Optional[int] = None
    error_message: Optional[str] = None
    metadata: dict = {}
    signature: str

@router.post("/api/open/editor-jobs")
async def receive_callback(payload: CallbackPayload, request: Request):
    # 1. Verify signature (optional but recommended)
    # is_valid = verify_callback_signature(payload.dict(), payload.signature)
    # if not is_valid:
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Find the editor job in database
    editor_job = await EditorJob.get(id=payload.job_id)
    if not editor_job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 3. Update the job status
    if payload.status == "completed":
        editor_job.status = "completed"
        editor_job.output_url = payload.output_url
        editor_job.processing_time = payload.processing_time_seconds
        editor_job.completed_at = datetime.now()
    elif payload.status == "failed":
        editor_job.status = "failed"
        editor_job.error_message = payload.error_message
    elif payload.status == "started":
        editor_job.status = "processing"
        editor_job.started_at = datetime.now()

    await editor_job.save()

    # 4. Return success response
    return {"success": True}
```

## Callback Payload Format

### Started Callback
```json
{
  "job_id": "ddf87452-5451-48b9-a6d2-3ad9bb4dc221",
  "status": "started",
  "timestamp": "2025-12-25T19:20:14.123Z",
  "metadata": {
    "internal_job_id": "88d72017-a89e-4f6c-b00f-4ca400a92943"
  },
  "signature": "hmac_sha256_signature"
}
```

### Completed Callback
```json
{
  "job_id": "ddf87452-5451-48b9-a6d2-3ad9bb4dc221",
  "status": "completed",
  "output_url": "https://taylorswiftnyu.s3.amazonaws.com/embedded/.../output.mp4",
  "processing_time_seconds": 120,
  "timestamp": "2025-12-25T19:22:14.123Z",
  "metadata": {
    "internal_job_id": "88d72017-a89e-4f6c-b00f-4ca400a92943",
    "sync_generation_id": "..."
  },
  "signature": "hmac_sha256_signature"
}
```

### Failed Callback
```json
{
  "job_id": "ddf87452-5451-48b9-a6d2-3ad9bb4dc221",
  "status": "failed",
  "error_code": "SYNC_FAILED",
  "error_message": "Lip-sync processing failed",
  "processing_time_seconds": 30,
  "timestamp": "2025-12-25T19:22:14.123Z",
  "metadata": {
    "internal_job_id": "88d72017-a89e-4f6c-b00f-4ca400a92943"
  },
  "signature": "hmac_sha256_signature"
}
```

## Signature Verification (Optional but Recommended)

MetaFrazo signs each callback with HMAC-SHA256 using `CALLBACK_HMAC_SECRET`.

### Verify signature in your endpoint:

```javascript
const crypto = require('crypto');

function verifyCallbackSignature(payload, receivedSignature) {
  const secret = process.env.CALLBACK_HMAC_SECRET; // Same as MetaFrazo's secret

  // Remove signature from payload before verification
  const { signature, ...dataToSign } = payload;

  // Create HMAC signature
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(JSON.stringify(dataToSign));
  const expectedSignature = hmac.digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(receivedSignature),
    Buffer.from(expectedSignature)
  );
}
```

## Testing the Full Flow

1. **Setup callback endpoint** (use ngrok or deploy Phraze.so)

2. **Generate JWT token** with correct callback URL:
   ```python
   python scripts/generate_jwt_token.py
   # Edit the script to use your public callback URL first
   ```

3. **Submit video job** via embedded editor

4. **Check your database** - the callback should update the job status

5. **Verify output video** is accessible via the S3 URL

## Current Test Output

Your latest job completed successfully:
- ✅ Job ID: `ddf87452-5451-48b9-a6d2-3ad9bb4dc221`
- ✅ Output URL: `https://taylorswiftnyu.s3.amazonaws.com/embedded/03139de3-8cc6-4702-a2fd-048dff642ccb/jobs/597c56f4-66d4-46d9-b12d-4bf3e34089cf/output.mp4`
- ✅ Processing completed

The callback **was sent** but failed to reach `localhost:3000`.

## Next Steps

1. Choose a solution (ngrok recommended for quick testing)
2. Implement the callback endpoint in Phraze.so
3. Test with a new video job
4. Verify the job status updates in your database

---

*Last updated: December 25, 2025*
