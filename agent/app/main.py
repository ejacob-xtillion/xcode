from datetime import datetime
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.router import register_routers
from app.core.logger import init_logger, get_logger
from app.core.errors.error_handler import register_error_handlers
from app.core.settings import get_settings
from app.core.middleware.request_logging import RequestLoggingMiddleware
from app.core.middleware.auth import JWTValidationMiddleware
from app.core.middleware.mcp_headers import HeaderForwardingMiddleware
from app.core.middleware.telemetry import TelemetryMiddleware
from app.core.telemetry.config import setup_telemetry, shutdown_telemetry
from app.core.telemetry.traces import instrument_fastapi
from contextlib import asynccontextmanager

settings = get_settings()
init_logger(settings)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log database configuration status
    if settings.async_database_url:
        logger.info("Database configured - using PostgreSQL for persistence")
    else:
        logger.warning("No database configured - using in-memory storage (data will be lost on restart)")

    setup_telemetry(settings)
    yield
    shutdown_telemetry()


description = (
    f"<b>Environment:</b> {settings.environment}<br>"
    f"<b>Version:</b> {settings.api_version}<br>"
    f"<b>Starting Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

app = FastAPI(
    title="REST API",
    description=description,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    version=settings.api_version,
    lifespan=lifespan,
)

if settings.is_development:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

app.add_middleware(RequestLoggingMiddleware)

# Conditionally add JWT middleware
if settings.jwt_enabled:
    if not settings.jwt_issuer or not settings.jwt_audience:
        logger.error("jwt_config_error", message="JWT enabled but jwt_issuer or jwt_audience not configured")
        raise ValueError("JWT_ENABLED=true requires JWT_ISSUER and JWT_AUDIENCE to be set in .env file")
    app.add_middleware(JWTValidationMiddleware, settings=settings)
    logger.info("jwt_middleware_enabled", issuer=settings.jwt_issuer, audience=settings.jwt_audience)
else:
    logger.warning(
        "jwt_middleware_disabled",
        message="API endpoints are not protected by JWT authentication. Set JWT_ENABLED=true in .env to enable.",
    )

# Add header forwarding middleware (runs on every request)
app.add_middleware(HeaderForwardingMiddleware)

if settings.otel_enabled:
    app.add_middleware(TelemetryMiddleware)

register_routers(app)
register_error_handlers(app)

if settings.otel_enabled:
    instrument_fastapi(app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)
