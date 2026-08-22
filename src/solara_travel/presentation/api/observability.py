"""Privacy-conscious structured events and HTTP request tracing."""

import json
import logging
from collections.abc import Awaitable, Callable, MutableMapping
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.types import Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
OBSERVABILITY_LOGGER_NAME = "solara_travel.api"
_SCHEMA_VERSION = 1


def configure_structured_logging() -> logging.Logger:
    """Configure one local JSON-message handler unless the host supplied one."""

    logger = logging.getLogger(OBSERVABILITY_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def emit_event(event: str, **fields: object) -> None:
    """Emit one versioned JSON object as one physical log message."""

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        **fields,
    }
    configure_structured_logging().info(json.dumps(payload, ensure_ascii=False))


def elapsed_milliseconds(started_at: float) -> float:
    """Return a non-negative monotonic duration in readable milliseconds."""

    return round(max(0.0, (perf_counter() - started_at) * 1000), 3)


def request_id_from_request(request: Request) -> str:
    """Return the server-owned request identifier stored by the middleware."""

    return str(request.state.request_id)


class RequestTracingMiddleware:
    """Attach a fresh server-owned request ID and emit safe request events."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        state = scope.setdefault("state", {})
        _store_request_id(state, request_id)
        started_at = perf_counter()
        status_code: int | None = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            if _should_log_request(scope["path"]):
                emit_event(
                    "http.request.exception",
                    request_id=request_id,
                    method=scope["method"],
                    path=scope["path"],
                    duration_ms=elapsed_milliseconds(started_at),
                    error_kind="unhandled",
                )
            raise

        if status_code is not None and _should_log_request(scope["path"]):
            emit_event(
                "http.request.completed",
                request_id=request_id,
                method=scope["method"],
                path=scope["path"],
                status_code=status_code,
                duration_ms=elapsed_milliseconds(started_at),
            )


def _store_request_id(state: MutableMapping[str, Any], request_id: str) -> None:
    state["request_id"] = request_id


def _should_log_request(path: str) -> bool:
    return path != "/health" and not path.startswith("/static/")
