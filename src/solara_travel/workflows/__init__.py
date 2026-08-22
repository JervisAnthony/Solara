"""Application workflow composition exposed by Solara."""

from solara_travel.workflows.hosted import HostedServices, build_hosted_services
from solara_travel.workflows.narration import (
    build_openai_recommendation_narration_service,
)
from solara_travel.workflows.offline import build_offline_recommendation_service

__all__ = [
    "HostedServices",
    "build_hosted_services",
    "build_offline_recommendation_service",
    "build_openai_recommendation_narration_service",
]
