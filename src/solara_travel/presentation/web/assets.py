"""Installed package-relative paths for Solara's browser resources."""

from hashlib import sha256
from pathlib import Path

PACKAGE_DIRECTORY = Path(__file__).resolve().parent
INDEX_DOCUMENT = PACKAGE_DIRECTORY / "templates" / "index.html"
STATIC_DIRECTORY = PACKAGE_DIRECTORY / "static"

FUNCTIONAL_ASSETS = (
    "travel-scopes.js",
    "inspiration.js",
    "selects.js",
    "app.js",
    "results.js",
    "itinerary.js",
    "feedback.js",
    "styles.css",
)


def asset_fingerprint(content: bytes) -> str:
    """Identify exact file bytes independently of path, time and package version."""
    return sha256(content).hexdigest()[:16]


def asset_url(filename: str) -> str:
    """Only packaged functional assets may be referenced by this renderer."""
    if filename not in FUNCTIONAL_ASSETS:
        raise ValueError("unsupported functional asset")
    fingerprint = asset_fingerprint((STATIC_DIRECTORY / filename).read_bytes())
    return f"/static/{filename}?v={fingerprint}"


def render_document() -> str:
    """Recalculate URLs from current package bytes; do not cache a stale manifest."""
    document = INDEX_DOCUMENT.read_text(encoding="utf-8")
    for filename in FUNCTIONAL_ASSETS:
        document = document.replace(f'/static/{filename}"', f'{asset_url(filename)}"')
    return document
