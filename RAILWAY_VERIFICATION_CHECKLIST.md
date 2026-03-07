# MetaFrazo Railway Deployment Verification Checklist

## Expected Railway Services

Based on your configuration files, you should have **4 services** deployed:

### 1. ✅ Backend Service
- **Dockerfile**: `Dockerfile.backend`
- **Config**: `railway.backend.toml`
- **Purpose**: FastAPI application (REST API)
- **Health Check**: `/health` endpoint
- **Port**: 8000

### 2. ✅ Worker Service
- **Dockerfile**: `Dockerfile.worker`
- **Config**: `railway.worker.toml`
- **Purpose**: Celery worker (processes video jobs)
- **No health check** (background service)

### 3. ⚠️ Beat Service (CRITICAL FOR CALLBACKS)
- **Dockerfile**: `Dockerfile.beat`
- **Config**: `railway.beat.toml`
- **Purpose**: Celery beat scheduler (sends callbacks to Cadence)
- **No health check** (background service)
- **Runs every 30 seconds**

### 4. ✅ Frontend Service
- **Dockerfile**: `Dockerfile.frontend`
- **Config**: `railway.frontend.toml`
- **Purpose**: React application (UI)
- **Health Check**: `/` endpoint
- **Port**: 80 (nginx)

### 5. ✅ PostgreSQL (Railway Add-on)
- **Purpose**: Database for video jobs
- **Auto-provisioned by Railway**

### 6. ✅ Redis (Railway Add-on)
- **Purpose**: Message broker for Celery
- **Auto-provisioned by Railway**

---

## How to Verify on Railway Dashboard

### Step 1: Check All Services Exist

Go to: https://railway.app/dashboard → Your Project

You should see **6 services**:
- [ ] backend
- [ ] worker
- [ ] **beat** ← **MOST IMPORTANT FOR YOUR ISSUE**
- [ ] frontend
- [ ] PostgreSQL
- [ ] Redis

### Step 2: Check Beat Service Status

Click on **beat** service:

**Deployments Tab:**
- [ ] Status: **Active** (green)
- [ ] Last deployed: Within last week
- [ ] Build: Successful

**Logs Tab** - Should show:
```
celery beat v5.3.4 is starting.
LocalTime -> 2026-03-04 19:30:00
Scheduler: Sending due task check-embedded-job-completion
```

If you see this repeating every 30 seconds → ✅ Beat is working

If you see errors or no logs → ❌ Beat is not working

### Step 3: Check Beat Service Environment Variables

Click **beat** service → **Variables** tab

Required variables:
```bash
# Database (auto-set by Railway)
DATABASE_URL=postgresql://...

# Redis (auto-set by Railway)
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...

# Phraze.so Integration (CRITICAL)
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_DOMAIN=phraze.so
EMBEDDED_MODE=true

# AWS (for downloading/uploading videos)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-2

# External APIs (for checking job status)
SYNC_API_KEY=...
GHOSTCUT_API_KEY=...
GHOSTCUT_APP_SECRET=...
GHOSTCUT_UID=...
```

### Step 4: Check Worker Service

Click **worker** service → **Logs**

Should show:
```
celery@worker ready.
```

If you see task processing logs → ✅ Worker is working

### Step 5: Check Backend Service

Click **backend** service → **Logs**

Should show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Test health endpoint:
```bash
curl https://your-backend-url.up.railway.app/health
# Should return: {"status":"healthy"}
```

---

## Common Issues & Fixes

### Issue 1: Beat Service Missing

**Symptom**: No "beat" service in Railway dashboard

**Fix**:
1. Go to Railway dashboard
2. Click **"+ New Service"**
3. Select **"Empty Service"**
4. Name: `beat`
5. Settings → Source → Connect to GitHub repo
6. Settings → Build → Dockerfile Path: `Dockerfile.beat`
7. Click **"Deploy"**

### Issue 2: Beat Service Exists but Not Running

**Symptom**: Beat service shows "Crashed" or "Stopped"

**Fix**:
1. Click beat service → **Logs** tab
2. Look for error messages
3. Common errors:
   - Missing environment variables → Add them in Variables tab
   - Cannot connect to Redis → Check Redis service is running
   - Cannot connect to PostgreSQL → Check PostgreSQL service is running

### Issue 3: Beat Running but No Callbacks Sent

**Symptom**: Beat logs show scheduler running, but Cadence not updating

**Check beat logs for**:
```
Checking embedded job {job_id}
Sync.so status = COMPLETED
Sending callback to https://phraze.so/api/editor/callback
Callback successful for job {job_id}
```

If you see "Callback failed" or connection errors:
- Check `PHRAZE_CALLBACK_URL` is correct
- Check Cadence `/api/editor/callback` endpoint is accessible
- Check callback URL matches your Cadence deployment (staging vs production)

### Issue 4: Wrong Callback URL

**Symptom**: Beat sends callbacks but to wrong URL

**Fix**:
1. Click beat service → **Variables**
2. Update `PHRAZE_CALLBACK_URL`:
   - Local: `http://localhost:3000/api/editor/callback`
   - Staging: `https://staging.phraze.so/api/editor/callback`
   - Production: `https://phraze.so/api/editor/callback`
3. Redeploy beat service

---

## Quick Verification Test

### Test 1: Check Beat Service Logs

```bash
# In Railway dashboard → beat service → Logs
# Look for this message every 30 seconds:
Scheduler: Sending due task check-embedded-job-completion
```

✅ If you see this → Beat scheduler is running
❌ If you don't see this → Beat is not working

### Test 2: Submit Test Job

1. Go to Cadence → Editor Jobs
2. Click "Open Editor" on a job
3. Submit the job in the editor
4. Wait 1-2 minutes for processing
5. Check beat service logs in Railway:
   ```
   Checking embedded job {job_id}
   Sending callback to https://phraze.so/api/editor/callback
   Callback successful
   ```
6. Refresh Cadence Editor Jobs page
7. Status should change from "syncing" to "quality_check"

✅ If status updates → Everything working!
❌ If status stays "syncing" → Beat not sending callbacks

---

## Environment Variables Reference

### Critical Variables for Beat Service

```bash
# Callback Configuration (MOST IMPORTANT)
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_DOMAIN=phraze.so
EMBEDDED_MODE=true

# Database (auto-set by Railway when you add PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis (auto-set by Railway when you add Redis)
REDIS_URL=redis://default:pass@host:6379
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# AWS (for video storage)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=your-bucket
AWS_REGION=us-east-2

# External APIs (for checking job completion)
SYNC_API_KEY=sk_...
GHOSTCUT_API_KEY=...
GHOSTCUT_APP_SECRET=...
GHOSTCUT_UID=...

# Optional
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

---

## What to Check Right Now

### Immediate Actions:

1. **Open Railway Dashboard**: https://railway.app/dashboard
2. **Find your MetaFrazo project**
3. **Count the services**: Should be 6 (backend, worker, beat, frontend, PostgreSQL, Redis)
4. **Click on "beat" service**:
   - If it doesn't exist → **CREATE IT** (see Issue 1 above)
   - If it exists → Check status (should be "Active")
   - If it's crashed → Check logs for errors
5. **Check beat logs**: Should see scheduler messages every 30 seconds
6. **Check beat variables**: Verify `PHRAZE_CALLBACK_URL` is correct

### If Beat Service is Missing:

This is **100% the cause** of your callback issue. You need to:
1. Create beat service in Railway
2. Deploy with `Dockerfile.beat`
3. Add all required environment variables
4. Wait for deployment to complete
5. Check logs to verify it's running

---

## Summary

Your deployment should have **4 application services**:
1. ✅ Backend (FastAPI)
2. ✅ Worker (Celery worker)
3. ⚠️ **Beat (Celery beat)** ← **CHECK THIS ONE**
4. ✅ Frontend (React)

Plus **2 database services**:
5. ✅ PostgreSQL
6. ✅ Redis

The **beat service** is critical for callbacks. Without it:
- Jobs complete in MetaFrazo ✅
- But Cadence never gets notified ❌
- Status stays "syncing" forever ❌

**Next Step**: Go to Railway dashboard and verify the beat service exists and is running!
