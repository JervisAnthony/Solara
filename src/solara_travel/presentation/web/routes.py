"""Browser document routes for Solara's static application shell."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from solara_travel.presentation.web.assets import INDEX_DOCUMENT

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_web_shell() -> HTMLResponse:
    """Return the packaged, credential-free Solara browser shell."""

    return HTMLResponse(INDEX_DOCUMENT.read_text(encoding="utf-8"))
