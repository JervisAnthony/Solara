"""FastAPI application factory and module-level ASGI entrypoint."""

from importlib import metadata

from fastapi import FastAPI

from solara_travel.presentation.api.routes.health import router as health_router
from solara_travel.presentation.api.settings import ApiSettings

_DISTRIBUTION_NAME = "solara-travel-ai"
_UNINSTALLED_VERSION = "0.0.0+uninstalled"


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Create a new credential-free FastAPI presentation application."""

    if settings is None:
        settings = ApiSettings()
    elif not isinstance(settings, ApiSettings):
        raise TypeError("settings must be ApiSettings or None")

    application = FastAPI(
        title="Solara Travel API",
        version=_application_version(),
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
    )
    application.include_router(health_router)
    return application


def _application_version() -> str:
    """Return installed distribution metadata or an explicit source fallback."""

    try:
        return metadata.version(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return _UNINSTALLED_VERSION


app = create_app()
