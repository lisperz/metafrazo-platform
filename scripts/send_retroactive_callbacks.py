"""
Script to manually send callbacks for completed embedded jobs
that were processed before the callback URL was configured
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.job import VideoJob, JobStatus
from backend.auth.phraze import PhrazeCallbackService
from backend.config import settings
from datetime import datetime

async def send_callbacks_for_completed_jobs():
    """Find completed embedded jobs and send callbacks"""

    # Create database connection
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Find completed embedded jobs that haven't sent callbacks
        completed_jobs = db.query(VideoJob).filter(
            VideoJob.is_embedded_job == True,
            VideoJob.status == JobStatus.COMPLETED.value,
            VideoJob.output_url.isnot(None)
        ).all()

        print(f"Found {len(completed_jobs)} completed embedded jobs")

        for job in completed_jobs:
            metadata = job.job_metadata or {}
            callback_url = metadata.get('phraze_callback_url')
            phraze_job_id = metadata.get('phraze_job_id')

            if not callback_url or not phraze_job_id:
                print(f"Job {job.id}: Missing callback info, skipping")
                continue

            print(f"\nJob {job.id}:")
            print(f"  Phraze Job ID: {phraze_job_id}")
            print(f"  Output URL: {job.output_url[:60]}...")
            print(f"  Callback URL: {callback_url}")

            # Calculate processing time
            processing_time = 0
            if job.started_at and job.completed_at:
                processing_time = int((job.completed_at - job.started_at).total_seconds())

            # Send callback
            print(f"  Sending callback...")
            success = await PhrazeCallbackService.notify_job_completed(
                callback_url=callback_url,
                job_id=phraze_job_id,
                output_url=job.output_url,
                processing_time_seconds=processing_time,
                metadata={
                    "internal_job_id": str(job.id),
                    "manual_callback": True,
                    "reason": "Retroactive callback for job completed before callback URL was configured"
                }
            )

            if success:
                print(f"  ✅ Callback sent successfully")
            else:
                print(f"  ❌ Callback failed")

        print(f"\n✅ Processed {len(completed_jobs)} jobs")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Sending callbacks for completed embedded jobs")
    print("=" * 60)
    asyncio.run(send_callbacks_for_completed_jobs())
