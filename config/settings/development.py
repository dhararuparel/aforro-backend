"""
Development-specific settings.

Extends base.py with development conveniences:
- Debug toolbar
- Relaxed security
- Verbose SQL logging
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Show SQL queries in development (enable selectively - can be noisy)
# To enable, set DJANGO_SQL_DEBUG=True in .env
import os
if os.environ.get("DJANGO_SQL_DEBUG") == "True":
    LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # noqa: F405

# Email backend (console for development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# DRF browsable API in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer"
)
