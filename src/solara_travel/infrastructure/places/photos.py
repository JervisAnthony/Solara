"""Transient Google Places Photos (New) integration for Postcards."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from urllib.parse import quote, urlsplit

from solara_travel.domain import Attraction, Destination
from solara_travel.infrastructure.http import (
    BinaryHttpGetTransport,
    JsonHttpDecodeError,
    JsonHttpTransport,
)
from solara_travel.ports import (
    PhotoAuthorAttribution,
    PhotoMedia,
    PostcardPhotoCandidate,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
)

_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PHOTO_FIELD_MASK = "places.displayName,places.photos"
_ALLOWED_MEDIA_HOSTS = frozenset(
    {"lh3.googleusercontent.com", "streetviewpixels-pa.googleapis.com"}
)
_ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@dataclass(frozen=True, slots=True)
class GooglePostcardMetadataProvider:
    """Discover fresh photo names and current attribution without persisting either."""

    api_key: str = field(repr=False)
    transport: JsonHttpTransport
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        _validate_configuration(self.api_key, self.timeout_seconds)

    def discover_postcard_photos(
        self,
        destination: Destination,
        attractions: tuple[Attraction, ...],
        *,
        limit: int,
    ) -> tuple[PostcardPhotoCandidate, ...]:
        """Use one bounded text search and return distinct provider-backed photos."""

        if not isinstance(destination, Destination):
            raise TypeError("destination must be a Destination")
        if not isinstance(attractions, tuple) or not all(
            isinstance(item, Attraction) for item in attractions
        ):
            raise TypeError("attractions must be a tuple of Attraction values")
        if type(limit) is not int or not 1 <= limit <= 4:
            raise ValueError("limit must be an integer between one and four")
        payload = self._post(
            {
                "textQuery": f"tourist attractions in {destination.name}, {destination.country}",
                "includedType": "tourist_attraction",
                "strictTypeFiltering": True,
                "languageCode": "en",
                "pageSize": 8,
            }
        )
        if not isinstance(payload, Mapping):
            raise ProviderResponseError("Google Places photo response must be an object")
        places = payload.get("places", [])
        if not isinstance(places, list):
            raise ProviderResponseError("Google Places photo places must be a list")
        candidates: list[PostcardPhotoCandidate] = []
        seen: set[str] = set()
        for place in places:
            if not isinstance(place, Mapping):
                raise ProviderResponseError("Google Places photo place must be an object")
            place_name = _display_name(place)
            photos = place.get("photos", [])
            if not isinstance(photos, list):
                raise ProviderResponseError("Google Places photos must be a list")
            for photo in photos:
                candidate = _photo_candidate(photo, place_name)
                if candidate.opaque_reference in seen:
                    continue
                seen.add(candidate.opaque_reference)
                candidates.append(candidate)
                break
            if len(candidates) == limit:
                break
        return tuple(candidates)

    def _post(self, payload: dict[str, object]) -> object:
        try:
            response = self.transport.post_json(
                url=_TEXT_SEARCH_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": _PHOTO_FIELD_MASK,
                },
                payload=payload,
                timeout_seconds=self.timeout_seconds,
            )
        except JsonHttpDecodeError as exc:
            raise ProviderResponseError("Google Places returned invalid photo JSON") from exc
        except Exception as exc:
            raise ProviderUnavailableError("Google Places photo metadata request failed") from exc
        _raise_for_google_status(response.status_code)
        return response.payload


@dataclass(frozen=True, slots=True)
class GooglePhotoMediaProvider:
    """Resolve a fresh photo URI server-side and retrieve bounded transient media."""

    api_key: str = field(repr=False)
    json_transport: JsonHttpTransport
    binary_transport: BinaryHttpGetTransport
    timeout_seconds: float = 10.0
    maximum_body_bytes: int = 8_000_000

    def __post_init__(self) -> None:
        _validate_configuration(self.api_key, self.timeout_seconds)
        if type(self.maximum_body_bytes) is not int or self.maximum_body_bytes <= 0:
            raise ValueError("maximum_body_bytes must be a positive integer")

    def retrieve_photo(
        self,
        opaque_reference: str,
        *,
        max_width_px: int,
        max_height_px: int,
    ) -> PhotoMedia:
        """Resolve media with skipHttpRedirect, then fetch the credential-free URI."""

        if not isinstance(opaque_reference, str) or not opaque_reference.startswith("places/"):
            raise ProviderResponseError("Google photo reference is invalid")
        if type(max_width_px) is not int or not 1 <= max_width_px <= 4800:
            raise ValueError("max_width_px must be between one and 4800")
        if type(max_height_px) is not int or not 1 <= max_height_px <= 4800:
            raise ValueError("max_height_px must be between one and 4800")
        endpoint = f"https://places.googleapis.com/v1/{quote(opaque_reference, safe='/')}/media"
        try:
            response = self.json_transport.get_json(
                url=endpoint,
                headers={"X-Goog-Api-Key": self.api_key},
                query={
                    "maxWidthPx": max_width_px,
                    "maxHeightPx": max_height_px,
                    "skipHttpRedirect": "true",
                },
                timeout_seconds=self.timeout_seconds,
            )
        except JsonHttpDecodeError as exc:
            raise ProviderResponseError("Google photo media response was invalid") from exc
        except Exception as exc:
            raise ProviderUnavailableError("Google photo media request failed") from exc
        _raise_for_google_status(response.status_code)
        if not isinstance(response.payload, Mapping):
            raise ProviderResponseError("Google photo media response must be an object")
        uri = response.payload.get("photoUri")
        if not isinstance(uri, str) or not _is_safe_photo_uri(uri):
            raise ProviderResponseError("Google photo media URI is invalid")
        try:
            media = self.binary_transport.get_bytes(
                url=uri,
                headers={"Accept": "image/avif,image/webp,image/jpeg,image/png"},
                timeout_seconds=self.timeout_seconds,
            )
        except Exception as exc:
            raise ProviderUnavailableError("Google photo content request failed") from exc
        _raise_for_google_status(media.status_code)
        content_type = (media.content_type or "").split(";", 1)[0].strip().lower()
        if content_type not in _ALLOWED_CONTENT_TYPES or not media.body:
            raise ProviderResponseError("Google photo content was not a supported image")
        if len(media.body) > self.maximum_body_bytes:
            raise ProviderResponseError("Google photo content exceeded the size limit")
        return PhotoMedia(media.body, content_type)


def _validate_configuration(api_key: object, timeout_seconds: object) -> None:
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key must be a non-blank string")
    if not isinstance(timeout_seconds, Real) or isinstance(timeout_seconds, bool):
        raise TypeError("timeout_seconds must be a real number")
    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be finite and greater than zero")


def _display_name(place: Mapping[str, object]) -> str:
    value = place.get("displayName")
    if not isinstance(value, Mapping):
        raise ProviderResponseError("Google photo place displayName must be an object")
    text = value.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ProviderResponseError("Google photo place name must be non-blank")
    return text.strip()


def _photo_candidate(photo: object, place_name: str) -> PostcardPhotoCandidate:
    if not isinstance(photo, Mapping):
        raise ProviderResponseError("Google photo must be an object")
    name = photo.get("name")
    width = photo.get("widthPx")
    height = photo.get("heightPx")
    google_maps_uri = photo.get("googleMapsUri")
    if (
        not isinstance(name, str)
        or type(width) is not int
        or width <= 0
        or type(height) is not int
        or height <= 0
        or not isinstance(google_maps_uri, str)
        or not google_maps_uri.startswith("https://www.google.com/maps/")
    ):
        raise ProviderResponseError("Google photo metadata is invalid")
    raw_attributions = photo.get("authorAttributions", [])
    if not isinstance(raw_attributions, list):
        raise ProviderResponseError("Google photo author attribution must be a list")
    attributions: list[PhotoAuthorAttribution] = []
    for attribution in raw_attributions:
        if not isinstance(attribution, Mapping):
            raise ProviderResponseError("Google photo author attribution must be an object")
        display_name = attribution.get("displayName")
        uri = attribution.get("uri")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ProviderResponseError("Google photo author display name is invalid")
        if uri is not None and (not isinstance(uri, str) or not uri.startswith("https://")):
            raise ProviderResponseError("Google photo author URI is invalid")
        attributions.append(PhotoAuthorAttribution(display_name.strip(), uri))
    return PostcardPhotoCandidate(
        name,
        place_name,
        width,
        height,
        google_maps_uri,
        tuple(attributions),
    )


def _is_safe_photo_uri(uri: str) -> bool:
    parsed = urlsplit(uri)
    return (
        parsed.scheme == "https"
        and parsed.hostname in _ALLOWED_MEDIA_HOSTS
        and parsed.username is None
        and parsed.password is None
    )


def _raise_for_google_status(status_code: int) -> None:
    if 200 <= status_code < 300:
        return
    if status_code in {401, 403}:
        raise ProviderAuthenticationError("Google Places photo authentication failed")
    if status_code == 429:
        raise ProviderRateLimitError("Google Places photo rate limit exceeded")
    if 400 <= status_code < 500:
        raise ProviderResponseError("Google Places photo request was rejected")
    if 500 <= status_code < 600:
        raise ProviderUnavailableError("Google Places photo service unavailable")
    raise ProviderResponseError("Google Places photo service returned an unexpected status")
