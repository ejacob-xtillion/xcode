from typing import Dict, Any, Optional


class AppError(Exception):
    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "GENERIC_ERROR",
        message: str = "An error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# 4xx - Client Errors
class BadRequestError(AppError):
    def __init__(
        self,
        message: str = "Bad Request",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(400, "BAD_REQUEST", message, details)


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Unauthorized",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(401, "UNAUTHORIZED", message, details)


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "Forbidden",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(403, "FORBIDDEN", message, details)


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource Not Found",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(404, "NOT_FOUND", message, details)


class MethodNotAllowedError(AppError):
    def __init__(
        self,
        message: str = "Method Not Allowed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(405, "METHOD_NOT_ALLOWED", message, details)


class UnprocessableEntityError(AppError):
    def __init__(
        self,
        message: str = "Unprocessable Entity",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(422, "UNPROCESSABLE_ENTITY", message, details)


class TooManyRequestsError(AppError):
    def __init__(
        self,
        message: str = "Too Many Requests",
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(429, "RATE_LIMIT_EXCEEDED", message, details)


# 5xx - Server Errors
class InternalServerError(AppError):
    def __init__(
        self,
        message: str = "Internal Server Error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(500, "INTERNAL_SERVER_ERROR", message, details)


class InternalProviderError(AppError):
    def __init__(
        self,
        message: str = "Internal Provider Error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(500, "PROVIDER_ERROR", message, details)


class DatabaseError(AppError):
    def __init__(
        self,
        message: str = "Database Error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(500, "DATABASE_ERROR", message, details)
