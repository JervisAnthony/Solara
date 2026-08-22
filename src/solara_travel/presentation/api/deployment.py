"""Environment-driven FastAPI factory for the hosted public alpha."""

from collections.abc import Mapping

from fastapi import FastAPI

from solara_travel.config import load_deployment_settings
from solara_travel.presentation.api.app import create_app
from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.settings import ApiSettings
from solara_travel.workflows.hosted import build_hosted_services


def create_deployment_app(
    *,
    environ: Mapping[str, str] | None = None,
) -> FastAPI:
    """Create one fully configured hosted application without startup I/O."""

    settings = load_deployment_settings(environ)
    services = build_hosted_services(settings)
    return create_app(
        ApiSettings(
            docs_enabled=settings.docs_enabled,
            public_alpha_safeguards=settings.public_alpha_safeguards,
        ),
        dependencies=ApiDependencies(
            recommendation_service=services.recommendation_service,
            narration_service=services.narration_service,
        ),
    )
