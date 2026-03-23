"""Minimal JWT validation middleware."""

from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.settings import get_settings, AppSettings
from app.core.errors.custom_errors import AppError, UnauthorizedError, InternalServerError
from app.core.errors.error_handler import app_error_to_json_response
from app.core.logger import get_logger
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

try:
    from jwt.exceptions import PyJWKClientKeyError
except ImportError:
    # PyJWKClientKeyError might not be available in all versions
    PyJWKClientKeyError = PyJWKClientError
from urllib.parse import urlparse

logger = get_logger()


class JWTValidationMiddleware(BaseHTTPMiddleware):
    """
    Minimal JWT validation middleware.

    Validates JWT tokens for:
    - Issuer
    - Audience
    - Expiry
    - Signature (using JWKS)

    Stores user claims in request.state.user
    """

    def __init__(self, app, settings: Optional[AppSettings] = None, exempt_paths: Optional[list[str]] = None):
        """Initialize middleware."""
        super().__init__(app)
        self.settings = settings or get_settings()

        # JWT configuration
        self.issuer = self.settings.jwt_issuer
        self.audience = self.settings.jwt_audience
        self.algorithms = self.settings.jwt_algorithms

        # Validate issuer format
        self._validate_issuer_format(self.issuer)

        # Initialize JWKS client for signature verification
        # Use configurable JWKS URL or default to issuer's well-known endpoint
        jwks_url = self.settings.jwt_jwks_url or f"{self.issuer.rstrip('/')}/.well-known/jwks.json"
        try:
            self.jwks_client = PyJWKClient(jwks_url, cache_keys=True)
            logger.info("jwks_client_initialized", jwks_url=jwks_url)
        except Exception as e:
            logger.error("jwks_client_init_failed", jwks_url=jwks_url, error=str(e))
            raise InternalServerError(
                f"Failed to initialize JWKS client with URL '{jwks_url}': {str(e)}",
                details={"jwks_url": jwks_url, "error": str(e)},
            )

        self.exempt_paths = exempt_paths or ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]

    def _validate_issuer_format(self, issuer: str) -> None:
        """
        Validate that the issuer URL is properly formatted.

        Args:
            issuer: The JWT issuer URL

        Raises:
            InternalServerError: If the issuer URL is invalid
        """
        if not issuer:
            raise InternalServerError("JWT issuer is not configured", details={"issuer": issuer})

        # Parse the URL to validate format
        parsed = urlparse(issuer)

        # Check for valid scheme (http or https)
        if not parsed.scheme or parsed.scheme not in ["http", "https"]:
            raise InternalServerError(
                f"JWT issuer must have a valid scheme (http or https): '{issuer}'",
                details={"issuer": issuer, "scheme": parsed.scheme},
            )

        # Check for valid netloc (domain)
        if not parsed.netloc:
            raise InternalServerError(f"JWT issuer must have a valid domain: '{issuer}'", details={"issuer": issuer})

        logger.debug("issuer_validated", issuer=issuer)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with JWT validation."""
        # Skip validation for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        try:
            # Extract Authorization header
            auth_header = request.headers.get("Authorization")

            if not auth_header:
                logger.warning("missing_auth_header", path=request.url.path)
                raise UnauthorizedError("Authorization header is required")

            # Parse token - support both "Bearer <token>" and "<token>" formats
            auth_header = auth_header.strip()
            parts = auth_header.split()

            if len(parts) == 2 and parts[0].lower() == "bearer":
                # Format: "Bearer <token>"
                token = parts[1]
            elif len(parts) == 1:
                # Format: "<token>" (without Bearer prefix)
                token = parts[0]
            else:
                logger.warning("invalid_auth_format", path=request.url.path)
                raise UnauthorizedError("Authorization header must be 'Bearer <token>' or '<token>'")

            # Validate JWT
            try:
                user_claims = self._validate_jwt(token)

                # Store user claims in request state
                request.state.user = user_claims

                logger.debug("jwt_validated", user_id=user_claims.get("sub"), path=request.url.path)

            except PyJWKClientError as e:
                # JWKS endpoint unreachable or key not found
                logger.warning("jwt_jwks_error", error=str(e), path=request.url.path)
                raise UnauthorizedError(f"Unable to verify JWT signature: {str(e)}")

            except (ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidTokenError) as e:
                # JWT validation errors (expired, invalid audience/issuer, malformed token)
                logger.warning(
                    "jwt_validation_failed", error=str(e), error_type=type(e).__name__, path=request.url.path
                )
                raise UnauthorizedError(f"Invalid JWT: {str(e)}")
            except (PyJWKClientConnectionError, PyJWKClientError) as e:
                # JWKS client errors (network issues, key not found, etc.)
                logger.error("jwks_client_error", error=str(e), error_type=type(e).__name__, path=request.url.path)
                raise InternalServerError(f"JWT validation service error: {str(e)}")
            except Exception as e:
                # Catch any other unexpected errors
                logger.error("unexpected_jwt_error", error=str(e), error_type=type(e).__name__, path=request.url.path)
                raise InternalServerError(f"Unexpected error during JWT validation: {str(e)}")

            response = await call_next(request)
            return response
        except AppError as exc:
            return app_error_to_json_response(exc)

    def _validate_jwt(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token.

        Validates:
        - Signature using JWKS
        - Issuer
        - Audience
        - Expiry

        Returns:
            Dict containing JWT claims
        """
        # Get signing key from JWKS
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=self.algorithms,
            audience=self.audience,
            issuer=self.issuer,
            options={"verify_signature": True, "verify_exp": True, "verify_aud": True, "verify_iss": True},
        )

        return payload
