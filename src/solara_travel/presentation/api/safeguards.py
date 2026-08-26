"""Identity-free, process-local safeguards for Solara's public alpha."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic
from types import TracebackType

from solara_travel.presentation.api.settings import PublicAlphaSafeguardSettings


@dataclass(frozen=True, slots=True)
class SafeguardRejection:
    """A safe rejected-admission result suitable for the HTTP boundary."""

    code: str
    retry_after_seconds: int


class RecommendationLease:
    """Release one admitted recommendation's concurrency slot on exit."""

    __slots__ = ("_safeguards",)

    def __init__(self, safeguards: "ApiSafeguards") -> None:
        self._safeguards = safeguards

    def __enter__(self) -> "RecommendationLease":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._safeguards._release_recommendation()


class ApiSafeguards:
    """Thread-safe rolling limits owned by exactly one application process."""

    def __init__(
        self,
        settings: PublicAlphaSafeguardSettings,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not isinstance(settings, PublicAlphaSafeguardSettings):
            raise TypeError("settings must be PublicAlphaSafeguardSettings")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._settings = settings
        self._clock = clock
        self._lock = Lock()
        self._recommendation_rate_events: deque[float] = deque()
        self._recommendation_budget_events: deque[float] = deque()
        self._feedback_events: deque[float] = deque()
        self._narration_events: deque[float] = deque()
        self._active_recommendations = 0

    def admit_recommendation(self) -> RecommendationLease | SafeguardRejection:
        """Atomically admit one recommendation or return its safe rejection."""

        with self._lock:
            if self._active_recommendations >= self._settings.recommendation_concurrency_limit:
                return SafeguardRejection("recommendation_capacity_reached", 1)

            now = self._clock()
            self._expire(
                self._recommendation_rate_events,
                now,
                self._settings.recommendation_rate_window_seconds,
            )
            self._expire(
                self._recommendation_budget_events,
                now,
                self._settings.recommendation_budget_window_seconds,
            )
            if len(self._recommendation_rate_events) >= self._settings.recommendation_rate_limit:
                return SafeguardRejection(
                    "recommendation_rate_limited",
                    self._retry_after(
                        self._recommendation_rate_events,
                        now,
                        self._settings.recommendation_rate_window_seconds,
                    ),
                )
            if (
                len(self._recommendation_budget_events)
                >= self._settings.recommendation_budget_limit
            ):
                return SafeguardRejection(
                    "recommendation_budget_exhausted",
                    self._retry_after(
                        self._recommendation_budget_events,
                        now,
                        self._settings.recommendation_budget_window_seconds,
                    ),
                )

            self._recommendation_rate_events.append(now)
            self._recommendation_budget_events.append(now)
            self._active_recommendations += 1
            return RecommendationLease(self)

    def admit_feedback(self) -> SafeguardRejection | None:
        """Consume one valid feedback slot or return a safe rejection."""

        with self._lock:
            now = self._clock()
            self._expire(
                self._feedback_events,
                now,
                self._settings.feedback_rate_window_seconds,
            )
            if len(self._feedback_events) >= self._settings.feedback_rate_limit:
                return SafeguardRejection(
                    "feedback_rate_limited",
                    self._retry_after(
                        self._feedback_events,
                        now,
                        self._settings.feedback_rate_window_seconds,
                    ),
                )
            self._feedback_events.append(now)
            return None

    def admit_narration(self) -> bool:
        """Consume one narration-attempt slot when budget remains."""

        with self._lock:
            now = self._clock()
            self._expire(
                self._narration_events,
                now,
                self._settings.narration_budget_window_seconds,
            )
            if len(self._narration_events) >= self._settings.narration_budget_limit:
                return False
            self._narration_events.append(now)
            return True

    def _release_recommendation(self) -> None:
        with self._lock:
            self._active_recommendations -= 1

    @staticmethod
    def _expire(events: deque[float], now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()

    @staticmethod
    def _retry_after(events: deque[float], now: float, window_seconds: int) -> int:
        return max(1, ceil(events[0] + window_seconds - now))
