from fastapi import HTTPException, status

from app.services.selection import SelectionError
from app.services.translation.provider import (
    TranslationNotConfiguredError,
    TranslationQuotaExceededError,
    TranslationTimeoutError,
)
from app.services.translation_service import TranslationRateLimitedError


def selection_error_response(exc: SelectionError) -> HTTPException:
    """422 with a machine-readable code (e.g. "selection_spans_lines") the frontend maps to a
    friendly message - never shown raw."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": exc.code, "message": exc.message},
    )


def translation_error_response(exc: Exception) -> HTTPException:
    """Maps a translation_service.RETRYABLE_TRANSLATION_ERRORS exception to the HTTP error
    the frontend already understands (shared by /translate and the vocabulary retry)."""
    if isinstance(exc, TranslationNotConfiguredError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "translation_not_configured",
                "message": "Translations aren't configured yet.",
            },
        )
    if isinstance(exc, TranslationRateLimitedError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "translation_rate_limited",
                "message": "Too many translation requests. Please try again later.",
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )
    if isinstance(exc, TranslationQuotaExceededError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "translation_quota_exceeded",
                "message": "The monthly translation quota has been used up.",
            },
        )
    if isinstance(exc, TranslationTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "translation_timeout",
                "message": "The translation service timed out. Please try again.",
            },
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "code": "translation_provider_error",
            "message": "The translation service is unavailable right now.",
        },
    )
