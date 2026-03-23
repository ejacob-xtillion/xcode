import logging
import structlog
from structlog.types import FilteringBoundLogger
import inspect
from opentelemetry import trace
from app.core.settings import AppSettings


def otel_trace_context_processor(logger, method_name, event_dict):
    span = trace.get_current_span()
    if span and span.is_recording():
        span_context = span.get_span_context()
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def init_logger(settings: AppSettings) -> None:
    is_dev = settings.is_development

    logging.basicConfig(
        format="%(message)s",
        level=settings.log_level,
        stream=None,  # Will use default (stdout)
    )

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        otel_trace_context_processor,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_dev:
        # Development: Colored console output for easy reading in Docker logs
        processors = shared_processors + [
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event=0,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]
    else:
        # Production: Logfmt for CloudWatch
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.LogfmtRenderer(
                key_order=["timestamp", "level", "logger", "event"],
                drop_missing=True,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> FilteringBoundLogger:
    if name is None:
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get("__name__", __name__)

    return structlog.get_logger(name)
