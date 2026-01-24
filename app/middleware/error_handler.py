"""
NEXUS Error Handling Middleware

Standardizes error responses and provides comprehensive error logging
for all API endpoints.
"""

import time
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
import logging

from ..logging_config import get_logger, log_error, log_request, log_response
from ..exceptions.manual_tasks import ManualInterventionRequired
from ..services.manual_task_manager import manual_task_manager
from decimal import Decimal
import json

logger = get_logger(__name__)


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj


class ErrorResponse:
    """Standard error response format."""

    @staticmethod
    def create(
        status_code: int,
        message: str,
        error_type: str,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create standardized error response."""
        response = {
            "error": {
                "code": status_code,
                "type": error_type,
                "message": message,
                "timestamp": time.time(),
            }
        }

        if request_id:
            response["error"]["request_id"] = request_id

        if details:
            response["error"]["details"] = details

        return response


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to handle errors and standardize responses.

    Features:
    - Request/response logging with timing
    - Standardized error responses
    - Request ID generation
    - Error categorization
    """
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Get user ID from request if available
    user_id = None
    # Extract user ID from headers if available (X-User-ID for testing)
    user_id_header = request.headers.get("x-user-id")
    if user_id_header:
        user_id = user_id_header
    # TODO: Extract user ID from authentication when implemented
    # For now, use placeholder or extract from headers if available

    # Log request
    log_request(
        logger,
        request_id=request_id,
        endpoint=request.url.path,
        method=request.method,
        user_id=user_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        log_response(
            logger,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )

        return response

    except RequestValidationError as exc:
        # Handle validation errors
        duration_ms = (time.time() - start_time) * 1000
        error_details = {
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, "body") else None,
        }
        # Convert Decimal objects for JSON serialization
        error_details = convert_decimals(error_details)

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            user_id=user_id,
            duration_ms=duration_ms,
            validation_errors=exc.errors(),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse.create(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Validation error",
                error_type="validation_error",
                request_id=request_id,
                details=error_details,
            ),
        )

    except HTTPException as exc:
        # Handle HTTP exceptions
        duration_ms = (time.time() - start_time) * 1000

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            user_id=user_id,
            duration_ms=duration_ms,
            status_code=exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.create(
                status_code=exc.status_code,
                message=str(exc.detail),
                error_type="http_error",
                request_id=request_id,
            ),
            headers=exc.headers if hasattr(exc, "headers") else None,
        )

    except ManualInterventionRequired as exc:
        # Handle manual intervention required exceptions
        duration_ms = (time.time() - start_time) * 1000

        # Log the manual task to database and markdown file
        try:
            task_id = await manual_task_manager.log_manual_task(exc)
        except Exception as task_error:
            logger.error(f"Failed to log manual task: {task_error}")
            # Fallback to just logging the error
            task_id = None

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            user_id=user_id,
            duration_ms=duration_ms,
            manual_task_id=task_id,
        )

        # Return structured error response with manual task ID
        error_details = {
            "task_id": task_id,
            "title": exc.title,
            "description": exc.description,
            "category": exc.category,
            "priority": exc.priority,
            "source_system": exc.source_system,
        }
        if exc.source_id:
            error_details["source_id"] = exc.source_id
        if exc.context:
            error_details["context"] = exc.context

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse.create(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Manual intervention required: {exc.title}",
                error_type="manual_intervention_required",
                request_id=request_id,
                details=error_details,
            ),
        )

    except Exception as exc:
        # Handle unexpected errors
        duration_ms = (time.time() - start_time) * 1000

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            user_id=user_id,
            duration_ms=duration_ms,
        )

        # Don't expose internal error details in production
        is_production = request.app.state.settings.get("environment", "development") == "production"
        error_message = "Internal server error" if is_production else str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.create(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_message,
                error_type="internal_error",
                request_id=request_id,
            ),
        )


def add_error_handlers(app: FastAPI) -> None:
    """Add error handlers to FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        request_id = getattr(request.state, "request_id", None)
        error_details = {
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, "body") else None,
        }
        # Convert Decimal objects for JSON serialization
        error_details = convert_decimals(error_details)

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            validation_errors=exc.errors(),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse.create(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Validation error",
                error_type="validation_error",
                request_id=request_id,
                details=error_details,
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        request_id = getattr(request.state, "request_id", None)

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.create(
                status_code=exc.status_code,
                message=str(exc.detail),
                error_type="http_error",
                request_id=request_id,
            ),
            headers=exc.headers if hasattr(exc, "headers") else None,
        )

    @app.exception_handler(ManualInterventionRequired)
    async def manual_intervention_handler(request: Request, exc: ManualInterventionRequired) -> JSONResponse:
        """Handle manual intervention required exceptions."""
        request_id = getattr(request.state, "request_id", None)

        # Log the manual task to database and markdown file
        try:
            task_id = await manual_task_manager.log_manual_task(exc)
        except Exception as task_error:
            logger.error(f"Failed to log manual task: {task_error}")
            # Fallback to just logging the error
            task_id = None

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            manual_task_id=task_id,
        )

        # Return structured error response with manual task ID
        error_details = {
            "task_id": task_id,
            "title": exc.title,
            "description": exc.description,
            "category": exc.category,
            "priority": exc.priority,
            "source_system": exc.source_system,
        }
        if exc.source_id:
            error_details["source_id"] = exc.source_id
        if exc.context:
            error_details["context"] = exc.context

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse.create(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Manual intervention required: {exc.title}",
                error_type="manual_intervention_required",
                request_id=request_id,
                details=error_details,
            ),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions."""
        request_id = getattr(request.state, "request_id", None)

        log_error(
            logger,
            exc,
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
        )

        # Don't expose internal error details in production
        is_production = request.app.state.settings.get("environment", "development") == "production"
        error_message = "Internal server error" if is_production else str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.create(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_message,
                error_type="internal_error",
                request_id=request_id,
            ),
        )


def setup_error_handling(app: FastAPI) -> None:
    """Setup error handling for FastAPI application."""
    # Add middleware
    app.middleware("http")(error_handler_middleware)

    # Add exception handlers
    add_error_handlers(app)

    logger.info("Error handling middleware configured")