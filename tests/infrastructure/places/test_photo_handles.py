"""Tests for short-lived tamper-resistant Postcards handles."""

import base64
import hashlib
import hmac
import json

import pytest

from solara_travel.infrastructure.places import SignedPhotoHandleCodec


def _codec(now: list[float] | None = None) -> SignedPhotoHandleCodec:
    clock = now or [100.0]
    return SignedPhotoHandleCodec(b"s" * 32, 30, lambda: clock[0])


def test_handle_round_trip_contains_no_api_credential() -> None:
    codec = _codec()
    handle = codec.encode("places/abc/photos/photo-1")

    assert codec.decode(handle) == "places/abc/photos/photo-1"
    assert "api" not in handle.casefold()
    assert "/" not in handle


@pytest.mark.parametrize("secret", [b"", b"short", "not-bytes"])
def test_codec_rejects_short_or_nonbyte_secret(secret: object) -> None:
    with pytest.raises(ValueError):
        SignedPhotoHandleCodec(secret=secret)  # type: ignore[arg-type]


@pytest.mark.parametrize("ttl", [True, 0, 901, 1.5])
def test_codec_rejects_invalid_ttl(ttl: object) -> None:
    with pytest.raises(ValueError):
        SignedPhotoHandleCodec(b"s" * 32, ttl)  # type: ignore[arg-type]


def test_codec_requires_callable_clock() -> None:
    with pytest.raises(TypeError):
        SignedPhotoHandleCodec(b"s" * 32, clock=None)  # type: ignore[arg-type]


@pytest.mark.parametrize("reference", [None, "", "places/x", "places/x/photos/a/more"])
def test_codec_rejects_invalid_reference(reference: object) -> None:
    with pytest.raises(ValueError):
        _codec().encode(reference)  # type: ignore[arg-type]


@pytest.mark.parametrize("handle", [None, "", "one", "a.b.c", "!.!"])
def test_codec_rejects_malformed_handle(handle: object) -> None:
    with pytest.raises(ValueError):
        _codec().decode(handle)  # type: ignore[arg-type]


def test_codec_rejects_tampering_and_expiry() -> None:
    now = [100.0]
    codec = _codec(now)
    handle = codec.encode("places/abc/photos/photo-1")
    payload, signature = handle.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    with pytest.raises(ValueError, match="signature"):
        codec.decode(f"{payload}.{signature[:-1]}{replacement}")

    now[0] = 130.0
    with pytest.raises(ValueError, match="expired"):
        codec.decode(handle)


def test_codec_rejects_signed_invalid_payload_shape_and_reference() -> None:
    codec = _codec()
    for payload_value in (
        {"expires": 130},
        {"expires": "soon", "reference": "places/a/photos/b"},
        {"expires": 130, "reference": "invalid"},
    ):
        payload = json.dumps(payload_value, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(b"s" * 32, payload, hashlib.sha256).digest()

        def encode(value: bytes) -> str:
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

        with pytest.raises(ValueError):
            codec.decode(f"{encode(payload)}.{encode(signature)}")
