# Testing Phraze.so Integration - Step by Step Guide

This guide walks you through testing the complete MetaFrazo + Phraze.so integration locally using ngrok.

## Prerequisites

✅ Phraze.so code at: `/Users/zhuchen/Downloads/cadence`
✅ MetaFrazo code at: `/Users/zhuchen/Downloads/metafrazo-platform`
✅ ngrok installed (`which ngrok` confirms it)
✅ Phraze.so `.env.local` configured with production database credentials

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Your Local Machine                                           │
│                                                               │
│  ┌─────────────────┐       ngrok tunnel                      │
│  │  Phraze.so      │◄─────https://abc123.ngrok.io           │
│  │  localhost:3000 │                                          │
│  └────────┬────────┘                                          │
│           │                                                   │
│           │ Connects to AWS RDS                              │
│           ▼                                                   │
│    Production Phraze.so Database                             │
│    (phraze-dev-instance-1.ccdrwsnbgg82.us-east-2.rds...)    │
└───────────────────────────────────────────────────────────────┘
                    ▲
                    │ Callbacks
                    │
            ┌───────┴────────┐
            │   MetaFrazo    │
            │    Railway     │
            │  (Cloud)       │
            └────────────────┘
```

---

## Step 1: Start Phraze.so Locally

### Terminal 1: Phraze.so Backend

```bash
cd /Users/zhuchen/Downloads/cadence

# Make sure .env.local is configured with AWS RDS credentials
cat .env.local | grep AWS_DB_HOST
# Should show: AWS_DB_HOST=phraze-dev-instance-1.ccdrwsnbgg82.us-east-2.rds.amazonaws.com

# Start the development server
npm run dev

# Wait for it to start...
# Should show: ✓ Ready on http://localhost:3000
```

**Keep this terminal running!**

---

## Step 2: Start ngrok Tunnel

### Terminal 2: ngrok

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform

# Start ngrok pointing to localhost:3000
ngrok http 3000

# You'll see output like:
# Forwarding   https://abc123def456.ngrok.io -> http://localhost:3000
#                      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
#                  COPY THIS URL!
```

**📋 Copy the https URL** (e.g., `https://abc123def456.ngrok.io`)

**Keep this terminal running!**

---

## Step 3: Create a Test Editor Job

We need to create a job in the Phraze.so database first, then generate a JWT token for it.

### Terminal 3: Create Job

```bash
cd /Users/zhuchen/Downloads/cadence

# Create a test editor job using the open API
curl -X POST "http://localhost:3000/api/open/editor-jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "03139de3-8cc6-4702-a2fd-048dff642ccb",
    "video_url": "https://taylorswiftnyu.s3.us-east-2.amazonaws.com/render_9bKalfgxFl2ydKtS1fJv.mp4",
    "processing_type": "lip_sync",
    "status": "pending"
  }'

# Response will include the job ID:
# {"success":true,"data":{"id":"<JOB_ID>",...}}
```

**📋 Copy the `id` from the response** (e.g., `550e8400-e29b-41d4-a716-446655440001`)

---

## Step 4: Generate JWT Token

Now generate a JWT token with your ngrok URL:

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform

# Replace YOUR-NGROK-URL with the URL from Step 2
# Replace JOB_ID with the ID from Step 3
python3 scripts/generate_jwt_token.py \
  https://YOUR-NGROK-URL.ngrok.io \
  JOB_ID

# Example:
# python3 scripts/generate_jwt_token.py \
#   https://abc123def456.ngrok.io \
#   550e8400-e29b-41d4-a716-446655440001
```

Wait, we need to update the script first to accept job_id...

Actually, let me create a better script:

```bash
cd /Users/zhuchen/Downloads/metafrazo-platform

# Use the existing script with your ngrok URL
python3 scripts/generate_jwt_with_custom_callback.py https://YOUR-NGROK-URL.ngrok.io

# Copy the Railway Frontend URL from the output
```

---

## Step 5: Test the Full Flow

### 5.1: Open the Embedded Editor

1. **Copy the Railway Frontend URL** from Step 4 output
2. **Paste it into your browser**
3. **You should see the embedded video editor load**

### 5.2: Submit a Video Job

1. **In the editor, add an audio segment**
2. **Upload or select audio**
3. **Click "Submit" or "Process"**

### 5.3: Watch the Logs

**In Terminal 1 (Phraze.so)**, you should see:

```
📥 MetaFrazo callback received: {
  job_id: 'test-job-1735162814',
  status: 'started',
  output_url: null,
  processing_time_seconds: undefined
}
✅ MetaFrazo callback processed successfully: {
  job_id: 'test-job-1735162814',
  new_status: 'started'
}

... wait a few minutes ...

📥 MetaFrazo callback received: {
  job_id: 'test-job-1735162814',
  status: 'completed',
  output_url: 'https://taylorswiftnyu.s3.amazonaws.com/embedded/...',
  processing_time_seconds: 120
}
✅ MetaFrazo callback processed successfully: {
  job_id: 'test-job-1735162814',
  new_status: 'completed'
}
```

---

## Step 6: Verify in Database

Check that the job was updated in the AWS RDS database:

```bash
# Query the editor_jobs table to see the updated job
curl "http://localhost:3000/api/open/editor-jobs?id=test-job-1735162814"

# You should see:
# {
#   "success": true,
#   "data": [{
#     "id": "test-job-1735162814",
#     "status": "completed",
#     "output_url": "https://taylorswiftnyu.s3.amazonaws.com/...",
#     "processing_time_seconds": 120,
#     "completed_at": "2025-12-25T..."
#   }],
#   ...
# }
```

---

## Expected Callback Flow

### 1. Job Started Callback

```json
{
  "job_id": "test-job-xxx",
  "status": "started",
  "timestamp": "2025-12-25T19:20:14Z",
  "metadata": {
    "internal_job_id": "..."
  }
}
```

**Phraze.so updates:**
- `status` → `started` or `processing`
- `started_at` → current timestamp

### 2. Job Completed Callback

```json
{
  "job_id": "test-job-xxx",
  "status": "completed",
  "output_url": "https://s3.amazonaws.com/...",
  "processing_time_seconds": 120,
  "timestamp": "2025-12-25T19:22:14Z",
  "metadata": {...}
}
```

**Phraze.so updates:**
- `status` → `completed`
- `output_url` → S3 URL of processed video
- `processing_time_seconds` → processing duration
- `completed_at` → current timestamp

### 3. Job Failed Callback (if error)

```json
{
  "job_id": "test-job-xxx",
  "status": "failed",
  "error_code": "SYNC_FAILED",
  "error_message": "Lip-sync processing failed",
  "processing_time_seconds": 30,
  "timestamp": "2025-12-25T19:20:44Z"
}
```

**Phraze.so updates:**
- `status` → `failed`
- `error_code` → error type
- `error_message` → error details
- `completed_at` → current timestamp

---

## Troubleshooting

### Callback Not Arriving

**Check ngrok terminal:**
- Look for POST requests to `/api/open/editor-jobs`
- If you see 404 or 400, check the endpoint path

**Check Phraze.so terminal:**
- Should see the callback logs
- If no logs, ngrok might be down or URL is wrong

**Check Railway worker logs:**
- Log into Railway dashboard
- Check the "worker" service logs
- Look for "Sending callback to..." messages

### Job Not Found Error

**Symptom:** Callback arrives but says "Editor job not found"

**Fix:**
- Make sure you created the job in Step 3 first
- Check the job_id matches between JWT token and database

### Database Not Updating

**Check the job status:**
```bash
curl "http://localhost:3000/api/open/editor-jobs?id=YOUR-JOB-ID"
```

**Check database credentials:**
```bash
cd /Users/zhuchen/Downloads/cadence
cat .env.local | grep AWS_DB
```

---

## Moving to Production

Once local testing works:

### 1. Deploy Phraze.so to Production

- Phraze.so already has the callback endpoint ready
- Just deploy to production (phraze.so domain)

### 2. Update JWT Generation

When Phraze.so generates JWT tokens in production:

```javascript
// In Phraze.so production code
const token = jwt.sign({
  iss: "phraze.so",
  sub: user_id,
  job_id: editor_job.id,
  video_url: video_url,
  callback_url: "https://phraze.so/api/open/editor-jobs",  // Production URL!
  permissions: ["edit", "process"],
  subscription_tier: user.subscription_tier,
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 86400,  // 24 hours
  jti: uuidv4()
}, privateKey, { algorithm: 'RS256' });
```

### 3. Configure MetaFrazo Railway

Make sure Railway backend has:
- `ENVIRONMENT=production`
- `PHRAZE_PUBLIC_KEY=<real public key from Phraze.so>`
- `CALLBACK_HMAC_SECRET=<coordinated secret>`

---

## Summary

✅ **Local Testing:** ngrok + localhost:3000 → AWS RDS database
✅ **Callback Endpoint:** `/api/open/editor-jobs` (PUT method)
✅ **Callback Format:** `job_id` parameter (MetaFrazo) → mapped to `id` (Phraze.so)
✅ **Production Ready:** Same endpoint works for production

---

*Last updated: December 25, 2025*
