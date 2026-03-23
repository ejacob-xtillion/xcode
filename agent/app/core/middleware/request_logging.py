import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.core.logger import get_logger

logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())

        is_health_check = request.url.path.startswith("/health")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        if not is_health_check:
            logger.info(
                "request_started",
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params) if request.query_params else None,
            )

        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        if not is_health_check:
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        response.headers["X-Request-ID"] = request_id

        return response
