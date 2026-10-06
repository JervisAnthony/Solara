"""Global operational build identity, independent of travellers and providers."""

import os
import re
from importlib import metadata
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReleaseResponse(BaseModel):
    product: Literal["Solara"] = "Solara"
    version: str
    source_revision: str | None


@router.get("/release", response_model=ReleaseResponse, include_in_schema=False)
def get_release() -> ReleaseResponse:
    """Expose an allowlist, not deployment configuration or request metadata."""
    revision = os.environ.get("RENDER_GIT_COMMIT", "")
    safe_revision = revision.lower() if re.fullmatch(r"[0-9a-fA-F]{40}", revision) else None
    try:
        version = metadata.version("solara-travel-ai")
    except metadata.PackageNotFoundError:
        version = "0.0.0+uninstalled"
    return ReleaseResponse(version=version, source_revision=safe_revision)
