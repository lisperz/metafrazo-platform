# Local Testing Guide - Phraze.so + MetaFrazo Integration

This guide helps you test the embedded editor integration locally before deploying to production.

## Problem

- MetaFrazo backend is on **Railway** (cloud)
- Phraze.so backend is on **localhost:3000** (your machine)
- Railway cannot reach localhost to send callbacks

## Solution: ngrok

ngrok creates a secure tunnel from the internet to your localhost:3000.

---

## Step 1: Start ngrok Tunnel

Open a **new terminal window** and run:

```bash
ngrok http 3000
```

You'll see output like:

```
Forwarding   https://abc123def456.ngrok.io -> http://localhost:3000
```

**Copy the https URL** (e.g., `https://abc123def456.ngrok.io`)

⚠️ **Keep this terminal running!** Don't close it during testing.

---

## Step 2: Add Callback Endpoint to Phraze.so

Add this endpoint to your Phraze.so backend to receive callbacks from MetaFrazo.

### For Express.js (Node.js):

Create or update `routes/editor-jobs.js`:

```javascript
const express = require('express');
const router = express.Router();

// POST /api/open/editor-jobs
// This receives callbacks from MetaFrazo when video jobs complete
router.post('/api/open/editor-jobs', async (req, res) => {
  try {
    const {
      job_id,
      status,
      output_url,
      processing_time_seconds,
      error_message,
      metadata
    } = req.body;

    console.log('📥 Received callback from MetaFrazo:', {
      job_id,
      status,
      output_url: output_url ? output_url.substring(0, 60) + '...' : null,
      processing_time_seconds
    });

    // Find the editor job in your database
    const editorJob = await db.editorJobs.findOne({
      where: { id: job_id }
    });

    if (!editorJob) {
      console.error('❌ Editor job not found:', job_id);
      return res.status(404).json({
        success: false,
        error: 'Job not found'
      });
    }

    // Update job based on callback status
    if (status === 'started') {
      editorJob.status = 'processing';
      editorJob.startedAt = new Date();
      console.log('✅ Job started:', job_id);

    } else if (status === 'completed') {
      editorJob.status = 'completed';
      editorJob.outputUrl = output_url;
      editorJob.processingTime = processing_time_seconds;
      editorJob.completedAt = new Date();
      console.log('✅ Job completed:', job_id, 'Output:', output_url);

    } else if (status === 'failed') {
      editorJob.status = 'failed';
      editorJob.errorMessage = error_message || 'Processing failed';
      editorJob.completedAt = new Date();
      console.error('❌ Job failed:', job_id, error_message);
    }

    // Save to database
    await editorJob.save();

    // Return success
    res.status(200).json({
      success: true,
      message: 'Callback processed successfully'
    });

  } catch (error) {
    console.error('❌ Error processing callback:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;
```

**Mount the router in your main app:**

```javascript
// In your app.js or index.js
const editorJobsRouter = require('./routes/editor-jobs');
app.use('/api/open', editorJobsRouter);
```

---

## Step 3: Generate JWT Token with ngrok URL

Use the ngrok URL you got from Step 1:

```bash
python3 scripts/generate_jwt_with_custom_callback.py https://abc123def456.ngrok.io
```

**Replace `abc123def456.ngrok.io` with YOUR ngrok URL!**

This will output:
- A test URL for the embedded editor
- The JWT token
- The callback URL that will be used

**Copy the Railway Frontend URL** from the output.

---

## Step 4: Test the Full Flow

1. **Make sure Phraze.so is running:**
   ```bash
   cd /path/to/phraze-so
   npm run dev  # or however you start it
   ```

2. **Make sure ngrok tunnel is running** (from Step 1)

3. **Open the test URL** in your browser (the Railway Frontend URL from Step 3)

4. **Submit a video job** in the embedded editor

5. **Watch your Phraze.so terminal** - you should see:
   ```
   📥 Received callback from MetaFrazo: { job_id: '...', status: 'started', ... }
   ✅ Job started: test-job-...

   📥 Received callback from MetaFrazo: { job_id: '...', status: 'completed', ... }
   ✅ Job completed: test-job-... Output: https://s3.amazonaws.com/...
   ```

6. **Check your database** - the editor job should be updated with:
   - `status: 'completed'`
   - `outputUrl: 'https://s3.amazonaws.com/...'`
   - `completedAt: <timestamp>`

---

## Step 5: Verify in Database

Query your database to see the updated job:

```sql
SELECT id, status, output_url, processing_time, completed_at
FROM editor_jobs
WHERE id = 'test-job-...';
```

You should see:
- `status` = `'completed'`
- `output_url` = The S3 URL of the processed video
- `completed_at` = Recent timestamp

---

## Troubleshooting

### ngrok tunnel not working

**Symptom:** Callbacks not arriving, no logs in Phraze.so terminal

**Check:**
1. Is ngrok still running? (Check the ngrok terminal)
2. Is the ngrok URL in the JWT token correct?
3. Try accessing `https://your-ngrok-url.ngrok.io` in browser - should show your Phraze.so app

### Job not found in database

**Symptom:** Callback arrives but says "Job not found"

**Fix:**
- Make sure you create the editor job in your database BEFORE generating the JWT token
- Or update the callback endpoint to create the job if it doesn't exist

### No callbacks arriving at all

**Check Railway worker logs:**
- The Celery worker should be running on Railway
- Look for logs like "Sending callback to ..." in the worker logs

---

## Moving to Production

Once local testing works, switch to production:

### For Production Phraze.so:

1. **No ngrok needed** - phraze.so is already public

2. **Generate production JWT tokens:**
   ```bash
   python3 scripts/generate_jwt_with_custom_callback.py https://phraze.so
   ```

3. **Deploy the callback endpoint** to production phraze.so

4. **Update your JWT generation service** on phraze.so to use:
   ```javascript
   const token = jwt.sign({
     // ... other fields
     callback_url: "https://phraze.so/api/open/editor-jobs"
   }, privateKey, { algorithm: 'RS256' });
   ```

5. **Done!** Production phraze.so will now receive callbacks from Railway

---

## Quick Reference

### Start ngrok:
```bash
ngrok http 3000
```

### Generate test token:
```bash
python3 scripts/generate_jwt_with_custom_callback.py https://YOUR-NGROK-URL.ngrok.io
```

### Callback endpoint:
```
POST /api/open/editor-jobs
```

### Expected callbacks:
1. `status: "started"` - Job processing started
2. `status: "completed"` - Job done, includes `output_url`
3. `status: "failed"` - Job failed, includes `error_message`

---

*Last updated: December 25, 2025*
