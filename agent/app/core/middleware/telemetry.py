import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger
from app.core.telemetry.instruments import (
    get_http_request_counter,
    get_http_request_duration,
)

logger = get_logger()


class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        try:
            attributes = {
                "http.method": request.method,
                "http.route": request.url.path,
                "http.status_code": response.status_code,
            }

            get_http_request_counter().add(1, attributes)
            get_http_request_duration().record(duration_ms, attributes)
        except Exception as e:
            logger.warning("failed_to_record_http_metrics", error=str(e))

        return response
