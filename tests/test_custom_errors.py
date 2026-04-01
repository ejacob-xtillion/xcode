import os
import sys
import types
import pytest

# Ensure the 'app' package (located under agent/app) is importable
CURRENT_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
AGENT_DIR = os.path.join(REPO_ROOT, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from app.core.errors.custom_errors import (
    AppError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    MethodNotAllowedError,
    UnprocessableEntityError,
    TooManyRequestsError,
    InternalServerError,
    InternalProviderError,
    DatabaseError,
)


def test_app_error_defaults():
    err = AppError()
    assert err.status_code == 500
    assert err.error_code == "GENERIC_ERROR"
    assert err.message == "An error occurred"
    assert err.details == {}
    # Exception message should be the provided message
    assert str(err) == err.message


def test_app_error_with_details():
    details = {"info": "extra", "code": 123}
    err = AppError(status_code=418, error_code="TEAPOT", message="I'm a teapot", details=details)
    assert err.status_code == 418
    assert err.error_code == "TEAPOT"
    assert err.message == "I'm a teapot"
    # details should be preserved (not mutated)
    assert err.details == details


@pytest.mark.parametrize(
    "exc_cls, expected_status, expected_code, msg",
    [
        (BadRequestError, 400, "BAD_REQUEST", "Bad Request"),
        (UnauthorizedError, 401, "UNAUTHORIZED", "Unauthorized"),
        (ForbiddenError, 403, "FORBIDDEN", "Forbidden"),
        (NotFoundError, 404, "NOT_FOUND", "Resource Not Found"),
        (MethodNotAllowedError, 405, "METHOD_NOT_ALLOWED", "Method Not Allowed"),
        (UnprocessableEntityError, 422, "UNPROCESSABLE_ENTITY", "Unprocessable Entity"),
        (InternalServerError, 500, "INTERNAL_SERVER_ERROR", "Internal Server Error"),
        (InternalProviderError, 500, "PROVIDER_ERROR", "Internal Provider Error"),
        (DatabaseError, 500, "DATABASE_ERROR", "Database Error"),
    ],
)
def test_specific_errors_defaults(exc_cls, expected_status, expected_code, msg):
    err = exc_cls()
    assert err.status_code == expected_status
    assert err.error_code == expected_code
    assert err.message == msg
    assert isinstance(err, AppError)


def test_specific_errors_custom_message_and_details():
    err = BadRequestError(message="Invalid input", details={"field": "name"})
    assert err.status_code == 400
    assert err.error_code == "BAD_REQUEST"
    assert err.message == "Invalid input"
    assert err.details == {"field": "name"}


def test_too_many_requests_retry_after_added_to_details():
    err = TooManyRequestsError(message="Slow down", retry_after=30)
    assert err.status_code == 429
    assert err.error_code == "RATE_LIMIT_EXCEEDED"
    assert err.message == "Slow down"
    # retry_after should be included in details when provided
    assert err.details.get("retry_after") == 30

    # When no details passed, details should still be a dict
    err2 = TooManyRequestsError()
    assert isinstance(err2.details, dict)
