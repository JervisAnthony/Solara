"""Public FastAPI presentation composition for Solara."""

from solara_travel.presentation.api.app import create_app
from solara_travel.presentation.api.settings import ApiSettings

__all__ = ["ApiSettings", "create_app"]
