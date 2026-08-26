"""Tests for Google geographic resolution and Autocomplete (New)."""

import pytest

from solara_travel.domain import DestinationQuery, TravelScopeKind
from solara_travel.infrastructure.http import JsonHttpResponse
from solara_travel.infrastructure.places.google import (
    GooglePlacesHttpClient,
    GooglePlacesProvider,
    normalize_google_travel_scope,
    normalize_google_travel_scope_suggestion,
)
from solara_travel.ports import ProviderResponseError, ProviderUnavailableError


class FakeTransport:
    def __init__(self, payload: object | None = None) -> None:
        self.payload = payload if payload is not None else {}
        self.calls: list[dict[str, object]] = []

    def post_json(self, **kwargs: object) -> JsonHttpResponse:
        self.calls.append(kwargs)
        return JsonHttpResponse(200, self.payload)


def _place(
    name: str = "Porto",
    primary_type: str = "locality",
    *,
    country: bool = True,
) -> dict[str, object]:
    components: list[dict[str, object]] = [
        {
            "longText": "Norte",
            "shortText": "Norte",
            "types": ["administrative_area_level_1"],
        }
    ]
    if country:
        components.append({"longText": "Portugal", "shortText": "PT", "types": ["country"]})
    return {
        "displayName": {"text": name},
        "location": {"latitude": 41.15, "longitude": -8.61},
        "addressComponents": components,
        "primaryType": primary_type,
        "types": [primary_type, "political"],
        "viewport": {
            "low": {"latitude": 40.5, "longitude": -9.0},
            "high": {"latitude": 42.0, "longitude": -7.5},
        },
    }


def _prediction(name: str, primary_type: str) -> dict[str, object]:
    return {
        "text": {"text": name},
        "primaryType": primary_type,
        "types": [primary_type, "political"],
    }


def test_http_client_uses_current_geographic_endpoints_and_minimal_masks() -> None:
    transport = FakeTransport()
    client = GooglePlacesHttpClient("test-key", transport, timeout_seconds=4)
    query = DestinationQuery("Port")

    client.search_travel_scope(query)
    client.autocomplete_travel_scopes(query)

    resolution, autocomplete = transport.calls
    assert resolution["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert resolution["payload"] == {
        "textQuery": "Port",
        "languageCode": "en",
        "pageSize": 1,
    }
    assert "places.primaryType" in resolution["headers"]["X-Goog-FieldMask"]  # type: ignore[index]
    assert autocomplete["url"] == "https://places.googleapis.com/v1/places:autocomplete"
    assert autocomplete["payload"] == {
        "input": "Port",
        "includedPrimaryTypes": ["(regions)"],
        "includeQueryPredictions": False,
        "languageCode": "en",
    }
    assert "placePrediction.text.text" in autocomplete["headers"]["X-Goog-FieldMask"]  # type: ignore[index]
    for method in (client.search_travel_scope, client.autocomplete_travel_scopes):
        with pytest.raises(TypeError, match="DestinationQuery"):
            method("Port")  # type: ignore[arg-type]


def test_normalization_maps_locality_country_region_and_multinational_region() -> None:
    locality = normalize_google_travel_scope(_place())
    country = normalize_google_travel_scope(_place("Portugal", "country"))
    region = normalize_google_travel_scope(_place("Norte", "administrative_area_level_1"))
    multinational = normalize_google_travel_scope(_place("Caribbean", "archipelago", country=False))

    assert locality.kind is TravelScopeKind.LOCALITY
    assert locality.containing_regions == ("Norte",)
    assert locality.viewport is not None
    assert country.kind is TravelScopeKind.COUNTRY
    assert region.kind is TravelScopeKind.REGION
    assert multinational.country_name is None


def test_scope_normalization_rejects_unknown_types_and_missing_country_for_locality() -> None:
    with pytest.raises(ProviderResponseError, match="supported travel scope"):
        normalize_google_travel_scope(_place("Museum", "museum"))
    with pytest.raises(ProviderResponseError, match="country identity"):
        normalize_google_travel_scope(_place(country=False))


@pytest.mark.parametrize("primary_type", ["locality", "postal_town", "country", "archipelago"])
def test_suggestion_normalization_maps_supported_types(primary_type: str) -> None:
    suggestion = normalize_google_travel_scope_suggestion(
        _prediction("  Place, Country  ", primary_type)
    )
    assert suggestion is not None
    assert suggestion.display_name == "Place, Country"


def test_suggestion_normalization_skips_unknown_and_rejects_bad_text() -> None:
    assert normalize_google_travel_scope_suggestion(_prediction("Museum", "museum")) is None
    assert normalize_google_travel_scope_suggestion({}) is None
    for prediction in (
        {"primaryType": "country", "text": "bad"},
        _prediction(" ", "country"),
    ):
        with pytest.raises(ProviderResponseError):
            normalize_google_travel_scope_suggestion(prediction)


class FakeClient:
    def __init__(self, resolution: object, autocomplete: object) -> None:
        self.resolution = resolution
        self.autocomplete = autocomplete

    def search_travel_scope(self, query: DestinationQuery) -> object:
        if isinstance(self.resolution, Exception):
            raise self.resolution
        return self.resolution

    def autocomplete_travel_scopes(self, query: DestinationQuery) -> object:
        if isinstance(self.autocomplete, Exception):
            raise self.autocomplete
        return self.autocomplete

    def search_destinations(self, request: object) -> object:
        return {"places": []}

    def search_destination(self, query: DestinationQuery) -> object:
        return {"places": []}

    def search_attractions(self, destination: object) -> object:
        return {"places": []}


def test_provider_resolves_and_bounds_supported_predictions() -> None:
    predictions = [
        {"placePrediction": _prediction(f"City {index}", "locality")} for index in range(6)
    ]
    predictions.insert(1, {"queryPrediction": {"text": "ignored"}})
    predictions.insert(2, {"placePrediction": _prediction("Museum", "museum")})
    provider = GooglePlacesProvider(
        FakeClient({"places": [_place()]}, {"suggestions": predictions})
    )

    assert provider.resolve_travel_scope(DestinationQuery("Porto")) is not None
    assert len(provider.suggest_travel_scopes(DestinationQuery("Cit"))) == 5
    empty = GooglePlacesProvider(FakeClient({"places": []}, {"suggestions": []}))
    assert empty.resolve_travel_scope(DestinationQuery("Missing")) is None


def test_provider_validates_queries_and_translates_unexpected_failures() -> None:
    provider = GooglePlacesProvider(FakeClient(RuntimeError("bad"), RuntimeError("bad")))
    with pytest.raises(TypeError, match="DestinationQuery"):
        provider.resolve_travel_scope("Porto")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="DestinationQuery"):
        provider.suggest_travel_scopes("Port")  # type: ignore[arg-type]
    with pytest.raises(ProviderUnavailableError):
        provider.resolve_travel_scope(DestinationQuery("Porto"))
    with pytest.raises(ProviderUnavailableError):
        provider.suggest_travel_scopes(DestinationQuery("Port"))
    propagated = GooglePlacesProvider(
        FakeClient(ProviderResponseError("bad response"), ProviderResponseError("bad response"))
    )
    with pytest.raises(ProviderResponseError):
        propagated.resolve_travel_scope(DestinationQuery("Porto"))
    with pytest.raises(ProviderResponseError):
        propagated.suggest_travel_scopes(DestinationQuery("Port"))


@pytest.mark.parametrize(
    "payload",
    [[], {"suggestions": "bad"}, {"suggestions": ["bad"]}],
)
def test_provider_rejects_malformed_autocomplete_payload(payload: object) -> None:
    provider = GooglePlacesProvider(FakeClient({"places": []}, payload))
    with pytest.raises(ProviderResponseError):
        provider.suggest_travel_scopes(DestinationQuery("Port"))


def test_scope_normalization_handles_optional_metadata_and_malformed_country_components() -> None:
    without_metadata = _place()
    without_metadata.pop("viewport")
    without_metadata["addressComponents"] = [
        "bad",
        {"types": "bad"},
        {"types": ["administrative_area_level_1"], "longText": " "},
        {"types": ["country"], "longText": "Portugal", "shortText": "PT"},
    ]
    scope = normalize_google_travel_scope(without_metadata)
    assert scope.viewport is None
    assert scope.containing_regions == ()
    multinational = _place("Caribbean", "archipelago", country=False)
    multinational.pop("addressComponents")
    assert normalize_google_travel_scope(multinational).containing_regions == ()

    missing_components = _place()
    missing_components.pop("addressComponents")
    with pytest.raises(ProviderResponseError, match="country identity"):
        normalize_google_travel_scope(missing_components)

    incomplete_country = _place()
    incomplete_country["addressComponents"] = [
        {"types": ["country"], "longText": "Portugal", "shortText": " "}
    ]
    with pytest.raises(ProviderResponseError, match="country identity"):
        normalize_google_travel_scope(incomplete_country)


@pytest.mark.parametrize(
    "viewport",
    [
        "bad",
        {},
        {"low": {}, "high": {}},
        {
            "low": {"latitude": 200, "longitude": 0},
            "high": {"latitude": 1, "longitude": 1},
        },
    ],
)
def test_scope_normalization_rejects_malformed_viewports(viewport: object) -> None:
    place = _place()
    place["viewport"] = viewport
    with pytest.raises(ProviderResponseError, match="viewport"):
        normalize_google_travel_scope(place)
