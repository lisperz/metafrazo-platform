# Railway Beat Service Fix - Callback System

## Problem

Jobs complete in MetaFrazo but Cadence still shows "syncing" because the **Celery Beat service** is not running on Railway to send callbacks.

## Solution: Deploy Beat Service to Railway

### Step 1: Check Current Services

1. Go to Railway Dashboard: https://railway.app/dashboard
2. Open your MetaFrazo project
3. Check which services are deployed:
   - ✅ **backend** (FastAPI)
   - ✅ **worker** (Celery worker)
   - ✅ **frontend** (React)
   - ❓ **beat** (Celery beat) ← **This might be missing!**
   - ✅ **PostgreSQL**
   - ✅ **Redis**

### Step 2: Deploy Beat Service

If the **beat** service is missing or not running:

#### Option A: Using Railway Dashboard (Easiest)

1. Go to your Railway project
2. Click **"+ New Service"**
3. Select **"Empty Service"**
4. Name it: `beat`
5. Go to **Settings** → **Source**
6. Connect to your GitHub repository
7. Set **Root Directory**: `/` (leave empty)
8. Set **Build Command**: (leave empty, uses Dockerfile)
9. Set **Dockerfile Path**: `Dockerfile.beat`
10. Click **"Deploy"**

#### Option B: Using Railway CLI

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform

# Login to Railway
railway login

# Link to your project
railway link

# Create beat service
railway service create beat

# Deploy beat service
railway up --service beat --detach
```

### Step 3: Configure Beat Service Environment Variables

The beat service needs the same environment variables as the worker:

1. Go to Railway Dashboard → Beat Service → **Variables**
2. Add these variables (copy from backend/worker service):

```bash
DATABASE_URL=postgresql://...  (auto-set by Railway)
REDIS_URL=redis://...          (auto-set by Railway)
CELERY_BROKER_URL=redis://...  (same as REDIS_URL)
CELERY_RESULT_BACKEND=redis://... (same as REDIS_URL)

# Phraze.so callback configuration
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_DOMAIN=phraze.so
EMBEDDED_MODE=true

# AWS credentials (for downloading/uploading results)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_S3_BUCKET=your-bucket
AWS_REGION=us-east-2

# API keys (for checking job status)
SYNC_API_KEY=your-sync-key
GHOSTCUT_API_KEY=your-ghostcut-key
GHOSTCUT_APP_SECRET=your-secret
GHOSTCUT_UID=your-uid
```

### Step 4: Verify Beat Service is Running

1. Go to Railway Dashboard → Beat Service
2. Check **Deployments** tab - should show "Active"
3. Check **Logs** tab - should see:

```
celery beat v5.3.4 is starting.
Scheduler: Sending due task check-embedded-job-completion
```

### Step 5: Test the Callback System

1. Submit a job from Cadence Editor Jobs
2. Wait for job to complete in MetaFrazo
3. Within 30 seconds, check beat service logs:

```
Checking embedded job {job_id}
Sync.so status = COMPLETED
Sending callback to https://phraze.so/api/editor/callback
Callback successful for job {job_id}
```

4. Refresh Cadence Editor Jobs page
5. Status should change from "syncing" to "quality_check"

## Troubleshooting

### Issue: Beat Service Keeps Crashing

**Check logs for errors:**
- Missing environment variables
- Cannot connect to Redis
- Cannot connect to PostgreSQL

**Fix:** Add missing environment variables in Railway dashboard

### Issue: Beat Service Running but No Callbacks

**Check beat service logs:**

```bash
# Look for this message every 30 seconds
Scheduler: Sending due task check-embedded-job-completion
```

If you don't see this, the beat schedule is not configured correctly.

**Check if jobs are marked as embedded:**

```sql
-- Connect to PostgreSQL via Railway
SELECT id, status, is_embedded_job, zhaoli_task_id
FROM video_jobs
WHERE is_embedded_job = true
AND status = 'processing'
ORDER BY created_at DESC
LIMIT 10;
```

If `is_embedded_job = false`, the jobs won't be picked up by the beat scheduler.

### Issue: Callback Sent but Cadence Not Updating

**Check callback URL in beat logs:**

```
Sending callback to https://phraze.so/api/editor/callback
```

Should match your Cadence deployment:
- Local: `http://localhost:3000/api/editor/callback`
- Staging: `https://staging.phraze.so/api/editor/callback`
- Production: `https://phraze.so/api/editor/callback`

**Fix:** Update `PHRAZE_CALLBACK_URL` environment variable in beat service

### Issue: Callback Returns 404 or 500

**Check Cadence logs** for errors at `/api/editor/callback`

**Test callback endpoint manually:**

```bash
curl -X POST https://phraze.so/api/editor/callback \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-job-id",
    "status": "completed",
    "output_url": "https://example.com/video.mp4"
  }'
```

Should return: `{"success":true,"message":"Job updated successfully"}`

## Railway Service Configuration Files

The beat service uses these files:

1. **`Dockerfile.beat`** - Defines the beat container
2. **`railway.beat.toml`** - Railway deployment config
3. **`backend/workers/celery_app.py`** - Celery configuration with beat schedule

## Beat Schedule Configuration

The beat scheduler runs these tasks:

```python
'check-embedded-job-completion': {
    'task': 'backend.workers.embedded_tasks.check_embedded_job_completion',
    'schedule': 30.0,  # Every 30 seconds
}
```

This task:
1. Queries PostgreSQL for embedded jobs with `status = 'processing'`
2. Checks Sync.so API for completion status
3. Downloads result from Sync.so and uploads to S3
4. Sends callback to Cadence with final video URL
5. Updates job status in PostgreSQL

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Services                          │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Backend  │───▶│  Worker  │───▶│ Sync.so  │             │
│  │ (FastAPI)│    │ (Celery) │    │   API    │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│                         │                                    │
│                         ▼                                    │
│                  ┌──────────────┐                           │
│                  │ PostgreSQL   │                           │
│                  │ (video_jobs) │                           │
│                  └──────────────┘                           │
│                         ▲                                    │
│                         │                                    │
│                  ┌──────────────┐                           │
│                  │ Beat Service │ ⚠️ MUST BE DEPLOYED      │
│                  │ (Scheduler)  │                           │
│                  └──────────────┘                           │
│                         │                                    │
│                         │ Every 30s: Check completed jobs   │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          │ HTTPS POST Callback
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cadence (phraze.so)                       │
│                                                              │
│  POST /api/editor/callback                                  │
│  {                                                           │
│    job_id: "abc-123",                                       │
│    status: "completed",                                     │
│    output_url: "s3://bucket/final.mp4"                     │
│  }                                                           │
│                          │                                   │
│                          ▼                                   │
│                  ┌──────────────┐                           │
│                  │    MySQL     │                           │
│                  │ UPDATE jobs  │                           │
│                  │ SET status = │                           │
│                  │ 'quality_check'                          │
│                  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Checklist

- [ ] Beat service exists in Railway project
- [ ] Beat service is deployed and running
- [ ] Beat service has all required environment variables
- [ ] Beat service logs show scheduler running every 30s
- [ ] `PHRAZE_CALLBACK_URL` points to correct Cadence URL
- [ ] Cadence `/api/editor/callback` endpoint is accessible
- [ ] Test job completes and callback is sent
- [ ] Cadence status updates from "syncing" to "quality_check"

## Commands for Railway CLI

```bash
# Login
railway login

# Link to project
railway link

# List services
railway service list

# Switch to beat service
railway service beat

# View logs
railway logs

# Deploy beat service
railway up --service beat

# Check environment variables
railway variables

# Set environment variable
railway variables set PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
```

## Summary

The beat service is a **critical component** for the callback system. Without it:
- ❌ Jobs complete in MetaFrazo but Cadence never knows
- ❌ Status stays "syncing" forever
- ❌ Users can't download final videos

With beat service running:
- ✅ Jobs complete in MetaFrazo
- ✅ Beat polls every 30s and detects completion
- ✅ Callback sent to Cadence
- ✅ Status updates to "quality_check"
- ✅ Final video URL populated
- ✅ Users can download results

**Next Step:** Go to Railway dashboard and verify the beat service is deployed and running!
