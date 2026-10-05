"""Future bounded planning, offer and snapshot storage ports; no live adapters."""

from datetime import date
from typing import TYPE_CHECKING, Protocol

from solara_travel.domain.destination import Destination
from solara_travel.domain.journey import JourneyOption
from solara_travel.domain.partners import PartnerCapability, PartnerOffer

if TYPE_CHECKING:
    from solara_travel.application.trip_export import TripSnapshot


class JourneyEvidencePort(Protocol):
    def options(
        self, origin: Destination, destination: Destination, departure_date: date, *, limit: int
    ) -> tuple[JourneyOption, ...]: ...


class PartnerOfferPort(Protocol):
    """Read-only future offer lookup; no transaction or redirect actions."""

    def offers(
        self, target_identity: str, capability: PartnerCapability, *, limit: int
    ) -> tuple[PartnerOffer, ...]: ...


class TripRepositoryPort(Protocol):
    """Future storage requires a separate access-control and retention design."""

    def save(self, identity: str, snapshot: "TripSnapshot") -> None: ...

    def load(self, identity: str) -> "TripSnapshot | None": ...
