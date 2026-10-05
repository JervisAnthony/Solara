"""Optional commerce contracts; no partner or offer is installed in production."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class PartnerKind(StrEnum):
    AGENCY = "agency"
    OPERATOR = "operator"
    ACCOMMODATION = "accommodation"
    ACTIVITY = "activity"
    TRANSPORT = "transport"


class PartnerCapability(StrEnum):
    ACTIVITIES = "activities"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    PACKAGES = "packages"
    HANDOFF = "handoff"


class OfferTargetKind(StrEnum):
    STAY = "stay"
    ACTIVITY = "activity"
    JOURNEY = "journey"


class OfferAvailability(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Partner:
    identity: str
    name: str
    kind: PartnerKind
    capabilities: tuple[PartnerCapability, ...]

    def __post_init__(self) -> None:
        for value in (self.identity, self.name):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("partner identity and name must be non-blank")
        if not isinstance(self.kind, PartnerKind):
            raise TypeError("kind must be PartnerKind")
        if not isinstance(self.capabilities, tuple) or not all(
            isinstance(item, PartnerCapability) for item in self.capabilities
        ):
            raise TypeError("capabilities must be a tuple of PartnerCapability")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("duplicate capabilities")

    def supports(self, capability: PartnerCapability) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True, slots=True)
class PartnerOffer:
    """External offer envelope attached by reference, never required by itinerary."""

    identity: str
    partner: Partner
    capability: PartnerCapability
    target_kind: OfferTargetKind
    target_identity: str
    retrieved_at: datetime
    availability: OfferAvailability  # required; no fabricated availability default
    amount: Decimal | None = None
    currency: str | None = None
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.identity, self.target_identity):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("offer references must be non-blank")
        if not isinstance(self.partner, Partner):
            raise TypeError("partner must be Partner")
        if not isinstance(self.capability, PartnerCapability):
            raise TypeError("capability must be PartnerCapability")
        if not self.partner.supports(self.capability):
            raise ValueError("partner does not support this capability")
        if not isinstance(self.target_kind, OfferTargetKind):
            raise TypeError("target_kind must be OfferTargetKind")
        if not isinstance(self.availability, OfferAvailability):
            raise TypeError("availability must be OfferAvailability")
        if not isinstance(self.retrieved_at, datetime) or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.valid_until is not None and (
            not isinstance(self.valid_until, datetime)
            or self.valid_until.utcoffset() is None
            or self.valid_until < self.retrieved_at
        ):
            raise ValueError("valid_until must be aware and not precede retrieval")
        if (self.amount is None) != (self.currency is None):
            raise ValueError("amount and currency must be supplied together")
        if self.amount is not None and (
            not isinstance(self.amount, Decimal) or not self.amount.is_finite() or self.amount < 0
        ):
            raise ValueError("amount must be a finite non-negative Decimal")
        if self.currency is not None and (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("currency must be a three-letter uppercase code")
