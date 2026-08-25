"""Same-origin transient photo delivery for traveller Postcards."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from solara_travel.application import InvalidPhotoHandleError
from solara_travel.ports import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)

router = APIRouter(prefix="/api/v1/postcards", tags=["postcards"])


@router.get("/{handle}", include_in_schema=False)
def postcard_photo(request: Request, handle: str) -> Response:
    """Verify a short-lived handle and stream transient image bytes without caching."""

    service = request.app.state.api_dependencies.photo_delivery_service
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Photo unavailable.")
    try:
        media = service.retrieve(handle)
    except InvalidPhotoHandleError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Photo unavailable.") from exc
    except (ProviderAuthenticationError, ProviderRateLimitError, ProviderUnavailableError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Photo temporarily unavailable."
        ) from exc
    except (ProviderResponseError, ProviderError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Photo unavailable.") from exc
    return Response(
        content=media.body,
        media_type=media.content_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
