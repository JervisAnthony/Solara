"""Installed package-relative paths for Solara's browser resources."""

from pathlib import Path

PACKAGE_DIRECTORY = Path(__file__).resolve().parent
INDEX_DOCUMENT = PACKAGE_DIRECTORY / "templates" / "index.html"
STATIC_DIRECTORY = PACKAGE_DIRECTORY / "static"
