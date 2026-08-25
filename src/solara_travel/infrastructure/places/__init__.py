"""Places-provider infrastructure exposed by Solara."""

from solara_travel.infrastructure.places.google import (
    GooglePlacesClient,
    GooglePlacesHttpClient,
    GooglePlacesProvider,
    normalize_google_attraction,
    normalize_google_destination,
)
from solara_travel.infrastructure.places.photo_handles import SignedPhotoHandleCodec
from solara_travel.infrastructure.places.photos import (
    GooglePhotoMediaProvider,
    GooglePostcardMetadataProvider,
)

__all__ = [
    "GooglePlacesClient",
    "GooglePlacesHttpClient",
    "GooglePlacesProvider",
    "GooglePhotoMediaProvider",
    "GooglePostcardMetadataProvider",
    "SignedPhotoHandleCodec",
    "normalize_google_attraction",
    "normalize_google_destination",
]
