-- Migration: Add embedded job support for phraze.so integration
-- Date: 2024-12-19
-- Description: Adds columns to support embedded mode video processing

-- Add is_embedded_job column to video_jobs table
ALTER TABLE video_jobs
ADD COLUMN IF NOT EXISTS is_embedded_job BOOLEAN DEFAULT FALSE;

-- Make user_id nullable for embedded jobs (they don't have local users)
ALTER TABLE video_jobs
ALTER COLUMN user_id DROP NOT NULL;

-- Add index for embedded jobs queries
CREATE INDEX IF NOT EXISTS idx_video_jobs_embedded ON video_jobs (is_embedded_job) WHERE is_embedded_job = TRUE;

-- Comment describing the change
COMMENT ON COLUMN video_jobs.is_embedded_job IS 'True for jobs created via phraze.so embedded integration';
