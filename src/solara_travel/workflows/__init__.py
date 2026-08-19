"""Application workflow composition exposed by Solara."""

from solara_travel.workflows.offline import build_offline_recommendation_service

__all__ = ["build_offline_recommendation_service"]
