from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from app.core.db.connection import engine
from app.core.logger import get_logger

logger = get_logger()


def setup_traces(settings, resource: Resource) -> Optional[TracerProvider]:
    if not settings.otel_enabled:
        return None

    try:
        tracer_provider = TracerProvider(resource=resource)

        if settings.otel_exporter_otlp_traces_endpoint:
            otlp_span_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_traces_endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))

        trace.set_tracer_provider(tracer_provider)

        if engine is not None:
            SQLAlchemyInstrumentor().instrument(
                engine=engine.sync_engine,
                enable_commenter=True,
            )
            logger.info("sqlalchemy_instrumentation_complete")
        else:
            logger.info("sqlalchemy_instrumentation_skipped", reason="no_database_configured")

        return tracer_provider
    except Exception as e:
        logger.error("traces_setup_failed", error=str(e), exc_info=True)
        raise


def instrument_fastapi(app) -> None:
    try:
        FastAPIInstrumentor().instrument_app(app)
        logger.info("fastapi_instrumentation_complete")
    except Exception as e:
        logger.error("fastapi_instrumentation_failed", error=str(e), exc_info=True)


def shutdown_traces(tracer_provider: Optional[TracerProvider]) -> None:
    if not tracer_provider:
        return

    try:
        tracer_provider.shutdown()

        fastapi_instrumentor = FastAPIInstrumentor()
        if fastapi_instrumentor._is_instrumented_by_opentelemetry:
            fastapi_instrumentor.uninstrument()

        # Only uninstrument SQLAlchemy if it was instrumented (i.e., if engine exists)
        if engine is not None:
            sqlalchemy_instrumentor = SQLAlchemyInstrumentor()
            if sqlalchemy_instrumentor.is_instrumented_by_opentelemetry:
                sqlalchemy_instrumentor.uninstrument()
    except Exception as e:
        logger.warning("traces_shutdown_failed", error=str(e))
