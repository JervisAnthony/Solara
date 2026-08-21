"""Public FastAPI presentation composition for Solara."""

from solara_travel.presentation.api.app import create_app
from solara_travel.presentation.api.dependencies import ApiDependencies
from solara_travel.presentation.api.settings import ApiSettings

__all__ = ["ApiDependencies", "ApiSettings", "create_app"]
