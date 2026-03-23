"""Header forwarding helper for downstream service calls.

Collects authorization, correlation ID, and forwarded headers
from incoming requests for forwarding to downstream services (MCP servers,
HTTP APIs, gRPC services, etc.).
"""

from typing import Callable, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from app.core.settings import get_settings
from app.core.logger import get_logger

logger = get_logger()

# Standard correlation ID header names (check in order)
CORRELATION_ID_HEADERS = ["X-Correlation-ID", "X-Request-ID"]


class HeaderForwardingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts and stores forwarded headers for downstream service calls.

    Runs on every request and stores headers in request.state.forwarded_headers.
    This ensures headers are prepared once per request and available for all downstream calls.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract headers and store in request.state, then continue with request."""
        headers = _extract_forwarded_headers_internal(request)
        request.state.forwarded_headers = headers

        response = await call_next(request)
        return response


def get_forwarded_headers(request: Request) -> Dict[str, str]:
    """
    Get forwarded headers for downstream service calls.

    Returns headers from request.state.forwarded_headers if middleware has run,
    otherwise extracts them on-demand.

    Merges:
    - Authorization header (from request headers)
    - Correlation ID (extracted from headers, optional)
    - Forwarded headers (from settings.header_forwarding)

    Args:
        request: FastAPI request object

    Returns:
        Dictionary of headers to forward to downstream services
    """
    # Use cached headers from middleware if available
    if hasattr(request.state, "forwarded_headers"):
        return request.state.forwarded_headers

    # Otherwise extract on-demand (backward compatibility)
    return _extract_forwarded_headers_internal(request)


def _extract_forwarded_headers_internal(request: Request) -> Dict[str, str]:
    """
    Internal function to extract forwarded headers from request.

    This is called by both the middleware and the helper function.
    """
    settings = get_settings()

    headers: Dict[str, str] = {}

    # 1. Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
        logger.debug("authorization_header_extracted")

    # 2. Extract correlation ID (optional) take this out
    correlation_id = _extract_correlation_id(request)
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
        logger.debug("correlation_id_set", correlation_id=correlation_id)

    # 3. Extract forwarded headers from settings
    configured_headers = _extract_forwarded_headers(request)
    headers.update(configured_headers)
    if configured_headers:
        logger.debug("forwarded_headers_extracted", count=len(configured_headers))

    # Log all headers being forwarded (masking sensitive values)
    sensitive_keys = {"authorization", "cookie", "x-api-key", "proxy-authorization"}
    safe_headers = {
        k: (
            "Bearer ***"
            if k.lower() == "authorization" and v.lower().startswith("bearer ")
            else "***" if k.lower() in sensitive_keys else v
        )
        for k, v in headers.items()
    }
    log_data = {"headers": safe_headers}
    if correlation_id:
        log_data["correlation_id"] = correlation_id
    logger.debug("forwarded_headers_collected", **log_data)

    # Add trace context to current span
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("forwarded.headers.count", len(headers))
        if correlation_id:
            span.set_attribute("forwarded.correlation_id", correlation_id)

    return headers


# Backward compatibility alias
get_mcp_headers = get_forwarded_headers


def _extract_correlation_id(request: Request) -> Optional[str]:
    """
    Extract correlation ID from request headers.

    Checks standard correlation ID headers in order:
    - X-Correlation-ID
    - X-Request-ID (set by RequestLoggingMiddleware)

    Returns None if no correlation ID is found in headers.

    Args:
        request: FastAPI request object

    Returns:
        Correlation ID string if found, None otherwise
    """
    # Check standard correlation ID headers
    for header_name in CORRELATION_ID_HEADERS:
        correlation_id = request.headers.get(header_name)
        if correlation_id:
            return correlation_id.strip()

    return None


def _extract_forwarded_headers(request: Request) -> Dict[str, str]:
    """
    Extract headers to forward based on settings.header_forwarding.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary of forwarded headers
    """
    settings = get_settings()
    headers: Dict[str, str] = {}

    # Get header forwarding configuration from settings
    header_forwarding = settings.header_forwarding
    if not header_forwarding:
        return headers

    # Support both string (single header) and list (multiple headers) formats
    # This handles edge cases where it might be set as a string in env vars
    if isinstance(header_forwarding, str):
        header_forwarding = [header_forwarding]

    # Extract each configured header
    for header_name in header_forwarding:
        header_value = request.headers.get(header_name)
        if header_value:
            headers[header_name] = header_value

    return headers
