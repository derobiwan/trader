"""
Celery application bootstrap for background processing.

The Docker stack launches Celery worker/beat services that expect a module
named `workspace.celery_app` exposing an `app` object. This lightweight
configuration wires Celery to Redis using the existing FastAPI settings.

Scheduled Tasks:
- Trading Cycle: Executes at configurable interval (default: 180 seconds)
  Configure via TRADING_CYCLE_INTERVAL_SECONDS environment variable
- Daily Report: Executes daily at midnight UTC
"""

from celery import Celery
from celery.schedules import crontab

from workspace.api.config import settings


def create_celery_app() -> Celery:
    """
    Create a Celery instance configured with Redis for broker and backend.

    Tasks are auto-discovered from the workspace.tasks module.
    Beat schedule is configured for:
    - Trading cycles at configurable interval (default: 180 seconds)
    - Daily reports at midnight UTC
    """

    celery = Celery(
        "trader",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "workspace.tasks.trading_cycle",
            "workspace.tasks.reporting",
        ],
    )

    # Get trading cycle interval from settings
    cycle_interval = settings.trading_cycle_interval_seconds
    task_expiry = max(10, cycle_interval - 10)  # Expire 10s before next run

    celery.conf.update(
        task_default_queue="default",
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        # Beat schedule for periodic tasks
        beat_schedule={
            # Trading cycle at configurable interval
            "trading-cycle-periodic": {
                "task": "trading_cycle.execute",
                "schedule": float(cycle_interval),
                "options": {
                    "expires": task_expiry,  # Expire before next run
                    "priority": 10,  # High priority
                },
            },
            # Daily performance report at midnight UTC
            "daily-report-midnight-utc": {
                "task": "reporting.generate_daily_report",
                "schedule": crontab(hour=0, minute=0),  # Midnight UTC
                "options": {
                    "expires": 3600,  # Expire after 1 hour
                },
            },
        },
        # Task result settings
        result_expires=3600,  # Results expire after 1 hour
        task_track_started=True,  # Track when tasks start
        task_time_limit=max(
            300, cycle_interval + 120
        ),  # Hard timeout: cycle + 2 min buffer
        task_soft_time_limit=max(
            270, cycle_interval + 90
        ),  # Soft timeout: cycle + 1.5 min buffer
        # Worker settings
        worker_prefetch_multiplier=1,  # Only fetch 1 task at a time
        worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    )

    return celery


# Celery expects a module-level `app` variable.
app = create_celery_app()
