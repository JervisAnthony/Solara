"""Tests for the Solara package foundation."""

from importlib import import_module
from importlib.metadata import metadata, version


def test_package_can_be_imported() -> None:
    """The installed Solara package should be importable."""

    package = import_module("solara_travel")

    assert package.__name__ == "solara_travel"


def test_installed_mvp1_release_metadata_is_alpha():
    assert version("solara-travel-ai") == "0.1.0"
    assert "Development Status :: 3 - Alpha" in metadata("solara-travel-ai").get_all("Classifier")
