"""Process-health route for Solara's FastAPI application."""

from fastapi import APIRouter

from solara_travel.presentation.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Confirm that the ASGI process is serving HTTP requests."""

    return HealthResponse(status="ok")
