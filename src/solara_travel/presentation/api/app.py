"""FastAPI application factory and module-level ASGI entrypoint."""

from importlib import metadata

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.observability import (
    RequestTracingMiddleware,
    configure_structured_logging,
)
from solara_travel.presentation.api.routes.feedback import router as feedback_router
from solara_travel.presentation.api.routes.health import router as health_router
from solara_travel.presentation.api.routes.recommendations import (
    router as recommendations_router,
)
from solara_travel.presentation.api.safeguards import ApiSafeguards
from solara_travel.presentation.api.settings import ApiSettings
from solara_travel.presentation.web.assets import STATIC_DIRECTORY
from solara_travel.presentation.web.routes import router as web_router

_DISTRIBUTION_NAME = "solara-travel-ai"
_UNINSTALLED_VERSION = "0.0.0+uninstalled"


def create_app(
    settings: ApiSettings | None = None,
    *,
    dependencies: ApiDependencies | None = None,
) -> FastAPI:
    """Create a new credential-free FastAPI presentation application."""

    if settings is None:
        settings = ApiSettings()
    elif not isinstance(settings, ApiSettings):
        raise TypeError("settings must be ApiSettings or None")

    if dependencies is None:
        dependencies = ApiDependencies()
    elif not isinstance(dependencies, ApiDependencies):
        raise TypeError("dependencies must be ApiDependencies or None")

    application = FastAPI(
        title="Solara Travel API",
        version=_application_version(),
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
    )
    configure_structured_logging()
    application.add_middleware(RequestTracingMiddleware)
    application.state.api_dependencies = dependencies
    application.state.api_safeguards = ApiSafeguards(settings.public_alpha_safeguards)
    application.include_router(web_router)
    application.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
    application.include_router(health_router)
    application.include_router(recommendations_router)
    application.include_router(feedback_router)
    return application


def _application_version() -> str:
    """Return installed distribution metadata or an explicit source fallback."""

    try:
        return metadata.version(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return _UNINSTALLED_VERSION


app = create_app()
