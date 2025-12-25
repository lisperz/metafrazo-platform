/**
 * Phraze.so Callback Endpoint Example
 *
 * This endpoint receives callbacks from MetaFrazo when video editing jobs
 * are processed (started, completed, or failed).
 *
 * Copy this file to your Phraze.so backend and adapt to your setup.
 */

// ============================================================================
// OPTION 1: Express.js API Route
// ============================================================================

const express = require('express');
const crypto = require('crypto');
const router = express.Router();

/**
 * Verify callback signature (RECOMMENDED for production)
 * This ensures the callback actually came from MetaFrazo
 */
function verifyCallbackSignature(payload, receivedSignature) {
  // Get the shared secret from environment variables
  const secret = process.env.CALLBACK_HMAC_SECRET;

  if (!secret) {
    console.warn('⚠️  CALLBACK_HMAC_SECRET not set - skipping signature verification');
    return true; // Skip verification in development
  }

  // Remove signature from payload before verification
  const { signature, ...dataToSign } = payload;

  // Create HMAC signature
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(JSON.stringify(dataToSign));
  const expectedSignature = hmac.digest('hex');

  // Compare signatures securely
  try {
    return crypto.timingSafeEqual(
      Buffer.from(receivedSignature),
      Buffer.from(expectedSignature)
    );
  } catch (e) {
    return false;
  }
}

/**
 * POST /api/open/editor-jobs
 * Receives callbacks from MetaFrazo embedded editor
 */
router.post('/api/open/editor-jobs', async (req, res) => {
  try {
    const {
      job_id,
      status,
      output_url,
      processing_time_seconds,
      error_code,
      error_message,
      metadata,
      signature,
      timestamp
    } = req.body;

    console.log('📥 MetaFrazo callback received:', {
      job_id,
      status,
      timestamp
    });

    // 1. Verify signature (RECOMMENDED for production)
    if (process.env.NODE_ENV === 'production' && signature) {
      const isValid = verifyCallbackSignature(req.body, signature);
      if (!isValid) {
        console.error('❌ Invalid callback signature for job:', job_id);
        return res.status(401).json({
          success: false,
          error: 'Invalid signature'
        });
      }
    }

    // 2. Find the editor job in your database
    // Replace this with your actual database query
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

    // 3. Update job based on callback status
    switch (status) {
      case 'started':
        editorJob.status = 'processing';
        editorJob.startedAt = new Date();
        editorJob.metafrazoJobId = metadata?.internal_job_id || null;
        console.log('✅ Job started:', job_id);
        break;

      case 'completed':
        editorJob.status = 'completed';
        editorJob.outputUrl = output_url;
        editorJob.processingTime = processing_time_seconds;
        editorJob.completedAt = new Date();
        console.log('✅ Job completed:', job_id);
        console.log('   Output URL:', output_url);
        console.log('   Processing time:', processing_time_seconds, 'seconds');

        // Optional: Notify user via email, webhook, etc.
        // await notifyUserJobComplete(editorJob.userId, output_url);
        break;

      case 'failed':
        editorJob.status = 'failed';
        editorJob.errorCode = error_code || 'UNKNOWN_ERROR';
        editorJob.errorMessage = error_message || 'Processing failed';
        editorJob.completedAt = new Date();
        console.error('❌ Job failed:', job_id);
        console.error('   Error:', error_message);

        // Optional: Notify user of failure
        // await notifyUserJobFailed(editorJob.userId, error_message);
        break;

      default:
        console.warn('⚠️  Unknown callback status:', status);
        return res.status(400).json({
          success: false,
          error: 'Unknown status'
        });
    }

    // 4. Save to database
    await editorJob.save();

    // 5. Return success response
    return res.status(200).json({
      success: true,
      message: 'Callback processed successfully',
      job_id: job_id,
      updated_status: editorJob.status
    });

  } catch (error) {
    console.error('❌ Error processing MetaFrazo callback:', error);
    return res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: error.message
    });
  }
});

module.exports = router;


// ============================================================================
// OPTION 2: Next.js API Route
// ============================================================================
// File: pages/api/open/editor-jobs.js (or app/api/open/editor-jobs/route.js for App Router)

import { NextApiRequest, NextApiResponse } from 'next';
import crypto from 'crypto';

function verifyCallbackSignature(payload, receivedSignature) {
  const secret = process.env.CALLBACK_HMAC_SECRET;

  if (!secret) {
    console.warn('⚠️  CALLBACK_HMAC_SECRET not set');
    return true;
  }

  const { signature, ...dataToSign } = payload;
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(JSON.stringify(dataToSign));
  const expectedSignature = hmac.digest('hex');

  try {
    return crypto.timingSafeEqual(
      Buffer.from(receivedSignature),
      Buffer.from(expectedSignature)
    );
  } catch (e) {
    return false;
  }
}

export default async function handler(req, res) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const {
      job_id,
      status,
      output_url,
      processing_time_seconds,
      error_message,
      metadata,
      signature
    } = req.body;

    console.log('📥 MetaFrazo callback:', { job_id, status });

    // Verify signature in production
    if (process.env.NODE_ENV === 'production' && signature) {
      const isValid = verifyCallbackSignature(req.body, signature);
      if (!isValid) {
        return res.status(401).json({ error: 'Invalid signature' });
      }
    }

    // Update database
    // Replace with your database logic
    const { prisma } = await import('@/lib/prisma');

    const editorJob = await prisma.editorJob.findUnique({
      where: { id: job_id }
    });

    if (!editorJob) {
      return res.status(404).json({ error: 'Job not found' });
    }

    // Update based on status
    const updateData = {};

    if (status === 'started') {
      updateData.status = 'processing';
      updateData.startedAt = new Date();
    } else if (status === 'completed') {
      updateData.status = 'completed';
      updateData.outputUrl = output_url;
      updateData.processingTime = processing_time_seconds;
      updateData.completedAt = new Date();
    } else if (status === 'failed') {
      updateData.status = 'failed';
      updateData.errorMessage = error_message;
      updateData.completedAt = new Date();
    }

    await prisma.editorJob.update({
      where: { id: job_id },
      data: updateData
    });

    console.log('✅ Job updated:', job_id, '→', updateData.status);

    return res.status(200).json({
      success: true,
      job_id,
      updated_status: updateData.status
    });

  } catch (error) {
    console.error('❌ Callback error:', error);
    return res.status(500).json({
      success: false,
      error: error.message
    });
  }
}


// ============================================================================
// Database Schema Example (Prisma)
// ============================================================================

/**
 * Add this to your schema.prisma file:
 *
 * model EditorJob {
 *   id                String   @id @default(uuid())
 *   userId            String
 *   videoUrl          String
 *   status            String   // "pending", "processing", "completed", "failed"
 *   outputUrl         String?
 *   processingTime    Int?     // in seconds
 *   errorMessage      String?
 *   errorCode         String?
 *   metafrazoJobId    String?  // Internal MetaFrazo job ID
 *
 *   createdAt         DateTime @default(now())
 *   startedAt         DateTime?
 *   completedAt       DateTime?
 *
 *   user              User     @relation(fields: [userId], references: [id])
 * }
 */


// ============================================================================
// Environment Variables Required
// ============================================================================

/**
 * Add to your .env file:
 *
 * # MetaFrazo Integration
 * CALLBACK_HMAC_SECRET=98b8cf5b9d4f5a33310bbcfb526cf2650889cefd0c32ac1f290a6a5526e5d5ef
 *
 * This secret must match the CALLBACK_HMAC_SECRET in MetaFrazo's Railway backend.
 */


// ============================================================================
// Testing the Callback Endpoint
// ============================================================================

/**
 * You can test this endpoint manually with curl:
 *
 * curl -X POST http://localhost:3000/api/open/editor-jobs \
 *   -H "Content-Type: application/json" \
 *   -d '{
 *     "job_id": "test-job-123",
 *     "status": "completed",
 *     "output_url": "https://s3.amazonaws.com/bucket/video.mp4",
 *     "processing_time_seconds": 120,
 *     "timestamp": "2025-12-25T12:00:00Z",
 *     "metadata": {
 *       "internal_job_id": "internal-123"
 *     }
 *   }'
 */
