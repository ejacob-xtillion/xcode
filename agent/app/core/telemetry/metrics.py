from typing import Optional
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from app.core.logger import get_logger

logger = get_logger()


def setup_metrics(settings, resource: Resource) -> Optional[MeterProvider]:
    if not settings.otel_enabled:
        return None

    try:
        metric_readers = []

        if settings.otel_export_console:
            console_metric_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=settings.otel_export_interval_millis,
            )
            metric_readers.append(console_metric_reader)

        if settings.otel_exporter_otlp_metrics_endpoint:
            otlp_metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_metrics_endpoint),
                export_interval_millis=settings.otel_export_interval_millis,
            )
            metric_readers.append(otlp_metric_reader)

        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)

        return meter_provider
    except Exception as e:
        logger.error("metrics_setup_failed", error=str(e), exc_info=True)
        raise


def shutdown_metrics(meter_provider: Optional[MeterProvider]) -> None:
    if not meter_provider:
        return

    try:
        meter_provider.shutdown()
    except Exception as e:
        logger.warning("metrics_shutdown_failed", error=str(e))
