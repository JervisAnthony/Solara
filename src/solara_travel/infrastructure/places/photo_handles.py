"""Short-lived stateless handles for transient Google photo resources."""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

_PHOTO_RESOURCE = re.compile(r"\Aplaces/[^/]+/photos/[^/]+\Z")


@dataclass(frozen=True, slots=True)
class SignedPhotoHandleCodec:
    """Sign expiring photo references with a startup-local random secret."""

    secret: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)
    ttl_seconds: int = 300
    clock: Callable[[], float] = time.time

    def __post_init__(self) -> None:
        if not isinstance(self.secret, bytes) or len(self.secret) < 32:
            raise ValueError("secret must contain at least 32 bytes")
        if type(self.ttl_seconds) is not int or not 1 <= self.ttl_seconds <= 900:
            raise ValueError("ttl_seconds must be an integer between one and 900")
        if not callable(self.clock):
            raise TypeError("clock must be callable")

    def encode(self, opaque_reference: str) -> str:
        """Return a URL-safe signed value containing no API credential."""

        reference = _validated_reference(opaque_reference)
        payload = json.dumps(
            {"expires": int(self.clock()) + self.ttl_seconds, "reference": reference},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.new(self.secret, payload, hashlib.sha256).digest()
        return f"{_encode(payload)}.{_encode(signature)}"

    def decode(self, handle: str) -> str:
        """Verify signature and expiry before returning the photo reference."""

        if not isinstance(handle, str) or handle.count(".") != 1:
            raise ValueError("photo handle is malformed")
        payload_text, signature_text = handle.split(".", 1)
        try:
            payload = _decode(payload_text)
            signature = _decode(signature_text)
            parsed = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("photo handle is malformed") from exc
        expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("photo handle signature is invalid")
        if not isinstance(parsed, dict) or set(parsed) != {"expires", "reference"}:
            raise ValueError("photo handle payload is invalid")
        expires = parsed["expires"]
        if type(expires) is not int or expires <= int(self.clock()):
            raise ValueError("photo handle has expired")
        return _validated_reference(parsed["reference"])


def _validated_reference(value: object) -> str:
    if not isinstance(value, str) or _PHOTO_RESOURCE.fullmatch(value) is None:
        raise ValueError("photo reference is invalid")
    return value


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
