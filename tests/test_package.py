"""Tests for the Solara package foundation."""

from importlib import import_module


def test_package_can_be_imported() -> None:
    """The installed Solara package should be importable."""

    package = import_module("solara_travel")

    assert package.__name__ == "solara_travel"