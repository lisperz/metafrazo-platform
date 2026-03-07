# Callback System Troubleshooting Guide

## Problem: Jobs Show "Processing" Forever in Cadence

When you submit a job in the MetaFrazo video editor, it completes in the MetaFrazo PostgreSQL database, but Cadence (phraze.so) still shows "syncing/processing" status.

## Root Cause

The **Celery Beat scheduler** is not running. This scheduler polls for completed jobs every 30 seconds and sends callbacks to Cadence to update the job status.

## Solution: Start Celery Beat

### Option 1: Using the Start Script (Recommended)

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform
./scripts/start-beat.sh
```

This will:
- Check Redis connection
- Start Celery beat scheduler
- Log output to `logs/beat.log`

### Option 2: Manual Start

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform
source .venv/bin/activate
cd backend
celery -A workers.celery_app beat --loglevel=info
```

### Option 3: Using Docker Compose

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform
docker-compose up -d beat
```

## Verify It's Working

### 1. Check Celery Beat Logs

```bash
tail -f /Users/zhuchen/Downloads/metafrazo-platform/logs/beat.log
```

You should see:
```
Scheduler: Sending due task check-embedded-job-completion
```

### 2. Check for Callback Attempts

```bash
# In MetaFrazo logs
grep "Sending callback" logs/beat.log
grep "Callback successful" logs/beat.log
```

### 3. Check Cadence Callback Endpoint

```bash
# In Cadence logs (if running locally)
# Look for POST requests to /api/editor/callback
```

## Complete Workflow

### Required Services

For the callback system to work, you need **3 services running**:

1. **MetaFrazo Backend** (FastAPI)
   ```bash
   ./scripts/start-backend.sh
   ```

2. **Celery Worker** (processes video jobs)
   ```bash
   ./scripts/start-worker.sh
   ```

3. **Celery Beat** (sends callbacks) ⚠️ **THIS IS THE MISSING PIECE**
   ```bash
   ./scripts/start-beat.sh
   ```

### Testing the Complete Flow

1. Start all MetaFrazo services:
   ```bash
   cd /Users/zhuchen/Downloads/metafrazo-platform
   ./scripts/start-backend.sh    # Terminal 1
   ./scripts/start-worker.sh     # Terminal 2
   ./scripts/start-beat.sh       # Terminal 3 (NEW!)
   ```

2. Start Cadence:
   ```bash
   cd /Users/zhuchen/Downloads/cadence
   npm run dev                   # Terminal 4
   ```

3. Submit a job from Cadence:
   - Go to Editor Jobs tab
   - Click "Open Editor"
   - Submit a job in the editor

4. Watch the logs:
   ```bash
   # MetaFrazo beat logs
   tail -f /Users/zhuchen/Downloads/metafrazo-platform/logs/beat.log

   # Look for:
   # - "Checking embedded job {job_id}"
   # - "Sync.so status = COMPLETED"
   # - "Sending callback to http://localhost:3000/api/editor/callback"
   # - "Callback successful for job {job_id}"
   ```

5. Verify in Cadence:
   - Refresh the Editor Jobs page
   - Status should change from "syncing" to "quality_check"
   - Final video URL should be populated

## Troubleshooting

### Issue: Celery Beat Not Finding Jobs

**Check PostgreSQL for embedded jobs:**
```sql
SELECT id, status, is_embedded_job, zhaoli_task_id
FROM video_jobs
WHERE is_embedded_job = true
AND status = 'processing';
```

### Issue: Callback URL Wrong

**Check the JWT token payload:**
```bash
cd /Users/zhuchen/Downloads/metafrazo-platform
python scripts/generate_jwt_token.py
```

The callback URL should be:
- Local: `http://localhost:3000/api/editor/callback`
- Staging: `https://staging.phraze.so/api/editor/callback`
- Production: `https://phraze.so/api/editor/callback`

### Issue: Callback Fails with Connection Error

**Check if Cadence is accessible:**
```bash
curl -X POST http://localhost:3000/api/editor/callback \
  -H "Content-Type: application/json" \
  -d '{"job_id":"test","status":"completed","output_url":"https://example.com/video.mp4"}'
```

Should return: `{"success":true,"message":"Job updated successfully"}`

### Issue: Redis Not Running

```bash
# Start Redis
docker-compose up -d redis

# Verify Redis is running
redis-cli -h localhost -p 6379 -a redis_password_123 ping
# Should return: PONG
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MetaFrazo Platform                        │
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
│                  │ Celery Beat  │ ⚠️ MUST BE RUNNING       │
│                  │ (Scheduler)  │                           │
│                  └──────────────┘                           │
│                         │                                    │
│                         │ Every 30s: Check for completed    │
│                         │ embedded jobs                      │
│                         ▼                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          │ HTTP POST Callback
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cadence Platform                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ POST /api/editor/callback                            │  │
│  │ {                                                     │  │
│  │   job_id: "abc-123",                                 │  │
│  │   status: "completed",                               │  │
│  │   output_url: "s3://bucket/final.mp4"               │  │
│  │ }                                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│                  ┌──────────────┐                           │
│                  │    MySQL     │                           │
│                  │    (jobs)    │                           │
│                  │              │                           │
│                  │ UPDATE jobs  │                           │
│                  │ SET status = │                           │
│                  │ 'quality_check'                          │
│                  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Fix Checklist

- [ ] Redis is running (`docker-compose up -d redis`)
- [ ] PostgreSQL is running (MetaFrazo database)
- [ ] MySQL is running (Cadence database)
- [ ] MetaFrazo backend is running (`./scripts/start-backend.sh`)
- [ ] Celery worker is running (`./scripts/start-worker.sh`)
- [ ] **Celery beat is running** (`./scripts/start-beat.sh`) ⚠️
- [ ] Cadence is running (`npm run dev`)
- [ ] Callback URL in JWT token is correct
- [ ] `/api/editor/callback` endpoint is accessible

## Environment Variables

### MetaFrazo (.env)

```bash
# Callback configuration
PHRAZE_CALLBACK_URL=http://localhost:3000/api/editor/callback
PHRAZE_DOMAIN=phraze.so
EMBEDDED_MODE=true

# Redis (for Celery)
REDIS_URL=redis://:redis_password_123@localhost:6379/0
CELERY_BROKER_URL=redis://:redis_password_123@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:redis_password_123@localhost:6379/0
```

### Cadence (.env.local)

```bash
# Editor configuration
NEXT_PUBLIC_EDITOR_URL=https://editor.phraze.so
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## Production Deployment

On Railway, ensure the **beat service** is deployed:

```bash
railway up --service beat --detach
```

Check beat service logs:
```bash
railway logs --service beat
```

## Summary

The key issue is that **Celery Beat must be running** for callbacks to work. Without it:
- Jobs complete in MetaFrazo ✅
- But Cadence never gets notified ❌
- Status stays "syncing" forever ❌

With Celery Beat running:
- Jobs complete in MetaFrazo ✅
- Beat polls every 30s and detects completion ✅
- Callback sent to Cadence ✅
- Status updates to "quality_check" ✅
