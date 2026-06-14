"""
Celery application configuration for Aforro Backend.

Celery is used for async processing of order confirmations
and any other background tasks.

Worker startup:
    celery -A config worker --loglevel=info
    celery -A config worker --loglevel=info --concurrency=4  (production)
"""

import os

from celery import Celery

# Set default Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("aforro")

# Load config from Django settings, namespace CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Debug task for verifying Celery is working correctly."""
    print(f"Request: {self.request!r}")
