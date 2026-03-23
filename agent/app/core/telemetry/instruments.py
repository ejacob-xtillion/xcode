from opentelemetry import metrics
from opentelemetry.metrics import Meter, Counter, Histogram
from typing import Optional

_meter: Optional[Meter] = None
_http_request_counter: Optional[Counter] = None
_http_request_duration: Optional[Histogram] = None


def get_meter() -> Meter:
    global _meter
    if _meter is None:
        _meter = metrics.get_meter(__name__)
    return _meter


def initialize_http_instruments() -> None:
    global _http_request_counter, _http_request_duration

    meter = get_meter()

    _http_request_counter = meter.create_counter(
        name="http.server.requests",
        description="Total number of HTTP requests",
        unit="1",
    )

    _http_request_duration = meter.create_histogram(
        name="http.server.duration",
        description="HTTP request duration in milliseconds",
        unit="ms",
    )


def get_http_request_counter() -> Counter:
    if _http_request_counter is None:
        raise RuntimeError("HTTP metrics not initialized. Call initialize_http_instruments() first.")
    return _http_request_counter


def get_http_request_duration() -> Histogram:
    if _http_request_duration is None:
        raise RuntimeError("HTTP metrics not initialized. Call initialize_http_instruments() first.")
    return _http_request_duration
