from typing import Optional
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from app.core.logger import get_logger
from app.core.telemetry.traces import setup_traces, shutdown_traces
from app.core.telemetry.metrics import setup_metrics, shutdown_metrics
from app.core.telemetry.instruments import initialize_http_instruments

logger = get_logger()

_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None


def setup_telemetry(settings) -> None:
    global _tracer_provider, _meter_provider

    if not settings.otel_enabled:
        return

    try:
        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": settings.api_version,
                "deployment.environment": settings.environment,
            }
        )

        _tracer_provider = setup_traces(settings, resource)
        _meter_provider = setup_metrics(settings, resource)
        initialize_http_instruments()

        logger.info(
            "telemetry_initialized",
            service=settings.otel_service_name,
            otlp_traces_endpoint=settings.otel_exporter_otlp_traces_endpoint or "none",
            otlp_metrics_endpoint=settings.otel_exporter_otlp_metrics_endpoint or "none",
            console_export=settings.otel_export_console,
        )
    except Exception as e:
        logger.error("telemetry_setup_failed", error=str(e), exc_info=True)
        raise


def shutdown_telemetry() -> None:
    global _tracer_provider, _meter_provider

    if not _tracer_provider and not _meter_provider:
        return

    try:
        shutdown_traces(_tracer_provider)
        shutdown_metrics(_meter_provider)
        logger.info("telemetry_shutdown_complete")
    except Exception as e:
        logger.warning("telemetry_shutdown_failed", error=str(e))
