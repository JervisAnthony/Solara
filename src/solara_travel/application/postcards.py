"""Non-fatal Postcards enrichment and photo delivery orchestration."""

from dataclasses import dataclass

from solara_travel.application.results import RecommendationResult
from solara_travel.domain import Destination
from solara_travel.ports.errors import ProviderError
from solara_travel.ports.photos import (
    PhotoAuthorAttribution,
    PhotoHandleCodec,
    PhotoMedia,
    PhotoMediaProvider,
    PostcardMetadataProvider,
)


class InvalidPhotoHandleError(ValueError):
    """A Postcards handle is malformed, tampered with, or expired."""


@dataclass(frozen=True, slots=True)
class PostcardPhoto:
    """Browser-safe photo metadata with a same-origin image path."""

    image_path: str
    place_name: str
    width_px: int
    height_px: int
    google_maps_uri: str
    author_attributions: tuple[PhotoAuthorAttribution, ...] = ()

    def __post_init__(self) -> None:
        if not self.image_path.startswith("/api/v1/postcards/"):
            raise ValueError("image_path must use the same-origin Postcards endpoint")
        if not self.place_name.strip():
            raise ValueError("place_name must not be blank")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("photo dimensions must be positive")
        if not self.google_maps_uri.startswith("https://www.google.com/maps/"):
            raise ValueError("google_maps_uri must be a Google Maps URL")


@dataclass(frozen=True, slots=True)
class DestinationPostcards:
    """Up to four transient photos for one authoritative recommendation."""

    destination: Destination
    photos: tuple[PostcardPhoto, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.destination, Destination):
            raise TypeError("destination must be a Destination")
        if not isinstance(self.photos, tuple):
            raise TypeError("photos must be a tuple")
        if len(self.photos) > 4:
            raise ValueError("photos must contain at most four values")
        if not all(isinstance(photo, PostcardPhoto) for photo in self.photos):
            raise TypeError("every photo must be a PostcardPhoto")


@dataclass(frozen=True, slots=True)
class PostcardCollection:
    """Destination-aligned Postcards enrichment for one result."""

    destinations: tuple[DestinationPostcards, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.destinations, tuple) or not all(
            isinstance(item, DestinationPostcards) for item in self.destinations
        ):
            raise TypeError("destinations must be a tuple of DestinationPostcards values")

    def for_destination(self, destination: Destination) -> DestinationPostcards | None:
        return next((item for item in self.destinations if item.destination == destination), None)


@dataclass(frozen=True, slots=True)
class PostcardEnrichmentService:
    """Discover photo metadata without making recommendations depend on it."""

    provider: PostcardMetadataProvider
    handle_codec: PhotoHandleCodec
    maximum_photos: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.provider, PostcardMetadataProvider):
            raise TypeError("provider must satisfy PostcardMetadataProvider")
        if not isinstance(self.handle_codec, PhotoHandleCodec):
            raise TypeError("handle_codec must satisfy PhotoHandleCodec")
        if type(self.maximum_photos) is not int or not 1 <= self.maximum_photos <= 4:
            raise ValueError("maximum_photos must be an integer between one and four")

    def enrich(self, result: RecommendationResult) -> PostcardCollection:
        if not isinstance(result, RecommendationResult):
            raise TypeError("result must be a RecommendationResult")
        enriched: list[DestinationPostcards] = []
        for recommendation in result.recommendations:
            try:
                candidates = self.provider.discover_postcard_photos(
                    recommendation.destination,
                    recommendation.evidence.attractions,
                    limit=self.maximum_photos,
                )
                photos = tuple(
                    PostcardPhoto(
                        image_path=f"/api/v1/postcards/{self.handle_codec.encode(item.opaque_reference)}",
                        place_name=item.place_name,
                        width_px=item.width_px,
                        height_px=item.height_px,
                        google_maps_uri=item.google_maps_uri,
                        author_attributions=item.author_attributions,
                    )
                    for item in candidates[: self.maximum_photos]
                )
            except (ProviderError, TypeError, ValueError):
                photos = ()
            enriched.append(DestinationPostcards(recommendation.destination, photos))
        return PostcardCollection(tuple(enriched))


@dataclass(frozen=True, slots=True)
class PhotoDeliveryService:
    """Verify a short-lived handle and retrieve bounded transient media."""

    handle_codec: PhotoHandleCodec
    provider: PhotoMediaProvider
    max_width_px: int = 1600
    max_height_px: int = 1200

    def __post_init__(self) -> None:
        if not isinstance(self.handle_codec, PhotoHandleCodec):
            raise TypeError("handle_codec must satisfy PhotoHandleCodec")
        if not isinstance(self.provider, PhotoMediaProvider):
            raise TypeError("provider must satisfy PhotoMediaProvider")
        if type(self.max_width_px) is not int or not 1 <= self.max_width_px <= 4800:
            raise ValueError("max_width_px must be between one and 4800")
        if type(self.max_height_px) is not int or not 1 <= self.max_height_px <= 4800:
            raise ValueError("max_height_px must be between one and 4800")

    def retrieve(self, handle: str) -> PhotoMedia:
        if not isinstance(handle, str) or not handle:
            raise InvalidPhotoHandleError("photo handle is invalid")
        try:
            reference = self.handle_codec.decode(handle)
        except (TypeError, ValueError) as exc:
            raise InvalidPhotoHandleError("photo handle is invalid") from exc
        return self.provider.retrieve_photo(
            reference,
            max_width_px=self.max_width_px,
            max_height_px=self.max_height_px,
        )
