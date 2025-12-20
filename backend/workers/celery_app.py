"""
Celery application configuration for video processing tasks
"""

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging
import os

from backend.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('video_processor')

# Configure Celery
app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    
    # Task routing
    task_routes={
        'backend.workers.video_tasks.process_video': {'queue': 'video_processing'},
        'backend.workers.video_tasks.check_ghostcut_status': {'queue': 'status_checks'},
        'backend.workers.video_tasks.cleanup_job': {'queue': 'cleanup'},
        'backend.workers.video_tasks.send_notification': {'queue': 'notifications'},
        'backend.workers.ghostcut_tasks.process_ghostcut_video': {'queue': 'video_processing'},
        'backend.workers.ghostcut_tasks.check_ghostcut_completion': {'queue': 'status_checks'}
    },
    
    # Task configuration for immediate processing
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_eager=False,  # Don't execute tasks immediately in the same process
    task_always_eager=False,  # Always use workers, not local execution
    broker_connection_retry_on_startup=True,  # Auto-retry connections
    broker_heartbeat=30,  # Short heartbeat for fast detection
    
    # Worker configuration for immediate task processing
    worker_prefetch_multiplier=1,  # Process one task at a time for video processing
    task_acks_late=True,
    worker_max_tasks_per_child=10,  # Restart workers after 10 tasks to prevent memory leaks
    worker_hijack_root_logger=False,  # Don't hijack logging
    worker_disable_rate_limits=True,  # Disable rate limits for immediate processing
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Task time limits - Remove limits for long-running video processing
    task_time_limit=None,  # No hard limit
    task_soft_time_limit=None,  # No soft limit
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-expired-files': {
            'task': 'backend.workers.video_tasks.core_tasks.cleanup_expired_files_task',
            'schedule': 3600.0,  # Run every hour
        },
        'update-user-quotas': {
            'task': 'backend.workers.video_tasks.core_tasks.update_user_quotas',
            'schedule': 24 * 3600.0,  # Run daily
        },
        'check-long-running-jobs': {
            'task': 'backend.workers.video_tasks.core_tasks.check_long_running_jobs',
            'schedule': 600.0,  # Run every 10 minutes (reduced from 5 due to smarter checking)
        },
        'update-processing-jobs-status': {
            'task': 'backend.workers.video_tasks.core_tasks.update_processing_jobs_status',
            'schedule': 120.0,  # Run every 2 minutes to keep status current
        },
        'check-ghostcut-completion': {
            'task': 'backend.workers.ghostcut_tasks.tasks.check_ghostcut_completion',
            'schedule': 120.0,  # Check every 2 minutes for completed jobs
        },
        'check-pro-job-completion': {
            'task': 'backend.workers.video_tasks.core_tasks.check_pro_job_completion',
            'schedule': 60.0,  # Check every minute for Pro job completion
        },
        'check-embedded-job-completion': {
            'task': 'backend.workers.embedded_tasks.check_embedded_job_completion',
            'schedule': 30.0,  # Check every 30 seconds for embedded job completion
        }
    }
)

# Task execution signals
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info(f"Task {task.name}[{task_id}] started with args={args}, kwargs={kwargs}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    logger.info(f"Task {task.name}[{task_id}] completed with state={state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Log task failure"""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")

# Import tasks to register them
from backend.workers import video_tasks
from backend.workers import ghostcut_tasks
from backend.workers import embedded_tasks

if __name__ == '__main__':
    app.start()