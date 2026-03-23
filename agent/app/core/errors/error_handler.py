from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logger import get_logger
from .custom_errors import AppError

logger = get_logger()


def app_error_to_json_response(exc: AppError) -> JSONResponse:
    response = {
        "status": exc.status_code,
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
    }
    headers = {}
    if hasattr(exc, "details") and exc.details and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    return JSONResponse(status_code=exc.status_code, content=response, headers=headers)


def register_error_handlers(app: FastAPI):

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        # Include traceback for 500-level errors
        include_traceback = exc.status_code >= 500

        # Use structured logging with context
        if exc.status_code >= 500:
            logger.error(
                "application_error",
                status_code=exc.status_code,
                error_code=exc.error_code,
                message=exc.message,
                path=request.url.path,
                method=request.method,
                exc_info=include_traceback,
            )
        else:
            logger.warning(
                "application_error",
                status_code=exc.status_code,
                error_code=exc.error_code,
                message=exc.message,
                path=request.url.path,
                method=request.method,
            )

        return app_error_to_json_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        fields = [".".join(str(loc) for loc in error["loc"]) for error in exc.errors()]

        logger.warning(
            "validation_error",
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            fields=fields,
            path=request.url.path,
            method=request.method,
        )

        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": fields},
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "status": 500,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "Internal Server Error",
                "details": {},
            },
        )
