# Phraze.so Callback Integration - Fix Summary

## Problem Found

MetaFrazo was sending callbacks via **POST** requests, but Phraze.so's `/api/open/editor-jobs` endpoint only handled:
- POST for creating NEW jobs
- PUT for updating jobs

Result: **400 Bad Request** errors for all callbacks.

## Solution Implemented

### Changes to Phraze.so Repository (`cadence`)

**File:** `src/app/api/open/editor-jobs/route.ts`

**Modified:** POST endpoint to handle BOTH job creation AND callbacks

**Logic:**
```typescript
POST /api/open/editor-jobs
  ↓
  Has job_id + status?
  ├─ Yes → Handle as MetaFrazo callback (update existing job)
  └─ No  → Handle as job creation (insert new job)
```

**What it does:**
1. **Detects callbacks:** Checks if request has `job_id` and `status` fields
2. **Updates job:** Maps callback data to database fields
3. **Sets timestamps:** Automatically sets `started_at`, `completed_at`, `callback_received_at`
4. **Logs everything:** Console logs for easy debugging
5. **Returns updated job:** Confirms the update was successful

**Callback fields supported:**
- `job_id` - Job identifier
- `status` - Job status (`started`, `completed`, `failed`)
- `output_url` - S3 URL of processed video
- `processing_time_seconds` - Processing duration
- `error_code` - Error type (if failed)
- `error_message` - Error details (if failed)

### New Testing Script

**File:** `scripts/test_phraze_callback_flow.py`

**Purpose:** Complete end-to-end testing

**What it does:**
1. Creates a job in Phraze.so database via API
2. Generates JWT token with that job's ID
3. Outputs test URLs for the embedded editor

**Usage:**
```bash
python3 scripts/test_phraze_callback_flow.py https://YOUR-NGROK-URL.ngrok.io
```

**Ensures:** The job exists in the database before testing callbacks

---

## Changes Summary

### Phraze.so (`cadence` repo)

| File | Lines Changed | Description |
|------|--------------|-------------|
| `src/app/api/open/editor-jobs/route.ts` | ~80 lines added | Handle callbacks in POST endpoint |

**Git commits:**
1. `9704a7e` - Support MetaFrazo callbacks with job_id parameter (PUT endpoint)
2. `134ae98` - Handle MetaFrazo callbacks in POST endpoint (main fix)

### MetaFrazo (`metafrazo-platform` repo)

| File | Type | Description |
|------|------|-------------|
| `scripts/test_phraze_callback_flow.py` | New | End-to-end testing script |
| `docs/TESTING_PHRAZE_INTEGRATION.md` | New | Complete testing guide |
| `docs/CALLBACK_SETUP_GUIDE.md` | New | Callback implementation guide |
| `docs/LOCAL_TESTING_GUIDE.md` | New | Local testing with ngrok |

---

## How to Share with Phraze.so Developer

### Option 1: Send Git Patch

```bash
cd /Users/zhuchen/Downloads/cadence

# Create patch file
git diff 872d807..134ae98 > phraze-metafrazo-callback-fix.patch

# Send the patch file to the developer
```

### Option 2: Share Commits

Tell the developer to pull commits:
- `9704a7e` - Support job_id in PUT endpoint
- `134ae98` - Handle callbacks in POST endpoint

### Option 3: Explain the Change

**Simple explanation:**

"The `/api/open/editor-jobs` POST endpoint now handles MetaFrazo callbacks. When a request has `job_id` and `status` fields, it updates the existing job instead of trying to create a new one. This fixes the 400 errors we were seeing."

**Key points:**
- ✅ No breaking changes to existing API
- ✅ Still creates jobs when `user_id` + `video_url` provided
- ✅ Now also updates jobs when `job_id` + `status` provided
- ✅ Adds comprehensive logging
- ✅ Handles all MetaFrazo callback scenarios

---

## Testing Checklist

### Before Testing
- [ ] Phraze.so running: `cd /Users/zhuchen/Downloads/cadence && npm run dev`
- [ ] ngrok running: `ngrok http 3000`
- [ ] ngrok URL copied

### Run Test
```bash
cd /Users/zhuchen/Downloads/metafrazo-platform
python3 scripts/test_phraze_callback_flow.py https://YOUR-NGROK-URL.ngrok.io
```

### Expected Output
```
✅ Job created successfully!
✅ JWT token generated!
📋 Test URLs: (copy the Railway URL)
```

### Test Flow
1. Open Railway URL in browser
2. Edit video and submit
3. Watch Phraze.so terminal for:
   ```
   📥 MetaFrazo callback received via POST: { job_id: '...', status: 'started' }
   ✅ MetaFrazo callback processed successfully

   ... wait 1-2 minutes ...

   📥 MetaFrazo callback received via POST: { job_id: '...', status: 'completed' }
   ✅ MetaFrazo callback processed successfully
   ```

### Verify in Database
```bash
curl 'https://YOUR-NGROK-URL.ngrok.io/api/open/editor-jobs?id=JOB-ID' | jq
```

Should show:
- `status: "completed"`
- `output_url: "https://s3.amazonaws.com/..."`
- `processing_time_seconds: 120`
- `completed_at: "2025-12-25T..."`

---

## Production Deployment

### For Phraze.so Developer

1. **Review and merge** the changes to `src/app/api/open/editor-jobs/route.ts`
2. **Deploy to production** phraze.so
3. **No configuration changes needed** - endpoint automatically detects callbacks

### For MetaFrazo (Already Done)

✅ MetaFrazo callbacks are already configured correctly
✅ Sending POST requests to callback URL
✅ Including all required fields

---

## Troubleshooting

### Still getting 400 errors?

**Check:**
1. Phraze.so has the updated code (commit `134ae98`)
2. Phraze.so was restarted after changes
3. ngrok is pointing to the right port (3000)

### Callbacks arriving but job not updated?

**Check:**
1. Job exists in database with the correct ID
2. Job ID in callback matches job ID in database
3. Check Phraze.so terminal logs for errors

### Job not found error?

**Solution:** Use `test_phraze_callback_flow.py` script - it creates the job first!

---

*Last updated: December 25, 2025*
