"""
Custom middleware for Aforro Backend.
"""

import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Logs incoming requests and their response times.

    Useful for performance monitoring and debugging.
    In production, consider using a dedicated APM tool instead.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.monotonic()

        response = self.get_response(request)

        duration_ms = (time.monotonic() - start_time) * 1000

        # Only log API requests to avoid noise
        if request.path.startswith("/api/") or request.path.startswith("/health/"):
            logger.info(
                "%s %s %s %.2fms",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )

        return response
