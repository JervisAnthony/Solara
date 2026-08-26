"""Provider-independent contracts for transient recommendation photography."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from solara_travel.domain import Attraction, Destination


@dataclass(frozen=True, slots=True)
class PhotoAuthorAttribution:
    """Attribution supplied with one provider-backed photo."""

    display_name: str
    profile_uri: str | None = None


@dataclass(frozen=True, slots=True)
class PostcardPhotoCandidate:
    """Transient metadata awaiting a short-lived same-origin handle."""

    opaque_reference: str
    place_name: str
    width_px: int
    height_px: int
    google_maps_uri: str
    author_attributions: tuple[PhotoAuthorAttribution, ...] = ()


@dataclass(frozen=True, slots=True)
class PhotoMedia:
    """Transient provider media returned through the same-origin boundary."""

    body: bytes
    content_type: str


@runtime_checkable
class PostcardMetadataProvider(Protocol):
    """Discover bounded photo metadata for one authoritative destination."""

    def discover_postcard_photos(
        self,
        destination: Destination,
        attractions: tuple[Attraction, ...],
        *,
        limit: int,
    ) -> tuple[PostcardPhotoCandidate, ...]:
        """Return transient, provider-backed photo candidates."""

        ...


@runtime_checkable
class PhotoMediaProvider(Protocol):
    """Retrieve one bounded photo without exposing provider credentials."""

    def retrieve_photo(
        self,
        opaque_reference: str,
        *,
        max_width_px: int,
        max_height_px: int,
    ) -> PhotoMedia:
        """Return transient image bytes for a fresh provider reference."""

        ...


@runtime_checkable
class PhotoHandleCodec(Protocol):
    """Create and verify short-lived tamper-resistant photo handles."""

    def encode(self, opaque_reference: str) -> str:
        """Encode one provider reference without an API credential."""

        ...

    def decode(self, handle: str) -> str:
        """Verify one handle and return its transient provider reference."""

        ...
