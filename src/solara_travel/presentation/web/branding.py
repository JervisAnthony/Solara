"""Presentation-only configuration boundary, not a deployed embed mode."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrandPresentation:
    """Text-only future branding. No remote assets, origins or partner assertions."""

    display_name: str = "Solara"
    embedded: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.display_name, str)
            or not self.display_name.strip()
            or len(self.display_name) > 80
            or not self.display_name.isprintable()
        ):
            raise ValueError("display_name must be printable text of 1 to 80 characters")
        if type(self.embedded) is not bool:
            raise TypeError("embedded must be boolean")
