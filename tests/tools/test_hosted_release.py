"""Offline operator-tool fixtures never contact Render or recommendation providers."""

import importlib.util
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

from solara_travel.presentation.api import ApiSettings, create_app
from solara_travel.presentation.web.assets import STATIC_DIRECTORY

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/verify_hosted_release.py"
_SPEC = importlib.util.spec_from_file_location("hosted_verifier_fixture", _SCRIPT)
verifier = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verifier)
BASE = "https://fixture.example"
SHA = "abcdef0123" * 4


@pytest.fixture
def operational_fixture(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", SHA)
    client = TestClient(create_app(ApiSettings(docs_enabled=False)))
    root = client.get("/")
    urls = re.findall(r'(?:src|href)="(/static/[^" ]+\?v=[0-9a-f]{16})"', root.text)
    responses = {}
    for path in ("/health", "/release", "/", "/docs", "/redoc", *urls):
        response = client.get(path)
        responses[path] = response.status_code, response.content
    calls = []

    def get(url):
        assert url.startswith(BASE)
        path = url[len(BASE) :]
        assert path in responses, "unexpected provider-consuming or external request"
        calls.append(path)
        return responses[path]

    return responses, get, calls


def test_valid_release_verifies_exact_checkout_without_provider_calls(operational_fixture):
    _, get, calls = operational_fixture
    assert verifier.verify(BASE, SHA.upper(), get=get)["version"] == "0.1.0"
    assert len(calls) == 13
    assert all(
        path == "/"
        or path.startswith("/static/")
        or path in ("/health", "/release", "/docs", "/redoc")
        for path in calls
    )


@pytest.mark.parametrize(
    "path,status,body",
    [
        ("/health", 500, b"{}"),
        ("/health", 200, b"{}"),
        ("/health", 200, b"[]"),
        ("/health", 200, b"bad"),
        ("/release", 404, b"{}"),
        ("/release", 200, b"{}"),
        (
            "/release",
            200,
            json.dumps({"product": "Other", "version": "0.1.0", "source_revision": SHA}).encode(),
        ),
        (
            "/release",
            200,
            json.dumps(
                {"product": "Solara", "version": "0.1.0.dev0", "source_revision": SHA}
            ).encode(),
        ),
        (
            "/release",
            200,
            json.dumps(
                {"product": "Solara", "version": "0.1.0", "source_revision": "bad"}
            ).encode(),
        ),
        (
            "/release",
            200,
            json.dumps({"product": "Solara", "version": "0.1.0", "source_revision": 1}).encode(),
        ),
        (
            "/release",
            200,
            json.dumps(
                {"product": "Solara", "version": "0.1.0", "source_revision": "0" * 40}
            ).encode(),
        ),
        (
            "/release",
            200,
            json.dumps({"product": "Solara", "version": "0.1.0", "source_revision": None}).encode(),
        ),
        ("/docs", 200, b"docs"),
        ("/redoc", 200, b"docs"),
        ("/", 404, b"missing"),
        ("/", 200, b"\xff"),
        ("/", 200, b"<html></html>"),
    ],
)
def test_operational_mismatches_fail_safely(operational_fixture, path, status, body):
    responses, get, _ = operational_fixture
    responses[path] = status, body
    with pytest.raises(verifier.VerificationError):
        verifier.verify(BASE, SHA, get=get)


@pytest.mark.parametrize("mutation", ["missing", "unversioned", "duplicate", "external", "unknown"])
def test_bad_asset_references_never_trigger_untrusted_requests(operational_fixture, mutation):
    responses, get, _ = operational_fixture
    document = responses["/"][1].decode()
    url = next(path for path in responses if path.startswith("/static/app.js"))
    changed = {
        "missing": document.replace(f'<script src="{url}" defer></script>', ""),
        "unversioned": document.replace(url, "/static/app.js"),
        "duplicate": document.replace(
            url, next(path for path in responses if path.startswith("/static/results.js"))
        ),
        "external": document.replace(url, "https://other.example/app.js"),
        "unknown": document.replace(url, url.replace("app.js", "unknown.js")),
    }[mutation]
    responses["/"] = 200, changed.encode()
    with pytest.raises(verifier.VerificationError):
        verifier.verify(BASE, SHA, get=get)


@pytest.mark.parametrize("failure", ["missing", "hash", "checkout"])
def test_asset_content_mismatches_are_detected(operational_fixture, failure, tmp_path):
    responses, get, _ = operational_fixture
    url = next(path for path in responses if path.startswith("/static/travel-scopes.js"))
    directory = STATIC_DIRECTORY
    if failure == "missing":
        responses[url] = 404, b"missing"
    elif failure == "hash":
        responses[url] = 200, b"wrong content"
    else:
        directory = tmp_path
        (directory / "travel-scopes.js").write_bytes(b"stale local bytes")
    with pytest.raises(verifier.VerificationError):
        verifier.verify(BASE, SHA, get=get, assets_directory=directory)
    if failure == "checkout":
        with pytest.raises(verifier.VerificationError, match="local release asset unavailable"):
            verifier.verify(BASE, SHA, get=get, assets_directory=tmp_path / "absent")


@pytest.mark.parametrize(
    "base",
    [
        "http://remote.example",
        "https://user:secret@fixture.example",
        "https://fixture.example/path",
        "https://fixture.example?key=secret",
        "https://fixture.example#fragment",
        "https://",
        "file:///tmp",
        "https://fixture.example:bad",
    ],
)
def test_operator_origin_is_validated_before_requests(base):
    with pytest.raises(verifier.VerificationError):
        verifier.verify(base, get=lambda _url: pytest.fail("must not request"))


def test_optional_sha_and_local_origin_policy(operational_fixture):
    responses, get, _ = operational_fixture
    responses["/release"] = (
        200,
        json.dumps({"product": "Solara", "version": "0.1.0", "source_revision": None}).encode(),
    )
    assert verifier.verify(BASE, get=get)["source_revision"] is None
    assert verifier._base_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    with pytest.raises(verifier.VerificationError):
        verifier.verify(BASE, "bad", get=get)


def test_cli_reports_safe_success_and_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        verifier,
        "verify",
        lambda *_args: {"product": "Solara", "version": "0.1.0", "source_revision": SHA},
    )
    assert verifier.main([BASE, "--expected-sha", SHA]) == 0
    assert SHA in capsys.readouterr().out

    def fail(*_args):
        raise verifier.VerificationError("deployed SHA mismatch")

    monkeypatch.setattr(verifier, "verify", fail)
    assert verifier.main([BASE]) == 1
    assert "deployed SHA mismatch" in capsys.readouterr().err


def test_fetch_bounds_reads_and_refuses_redirects(monkeypatch):
    class Response(BytesIO):
        code = 200

    class Opener:
        def __init__(self, result):
            self.result = result

        def open(self, request, timeout):
            assert request.get_method() == "GET" and timeout == 20
            assert request.headers["Accept-encoding"] == "identity"
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

    monkeypatch.setattr(verifier, "build_opener", lambda *_: Opener(Response(b"ok")))
    assert verifier.fetch(BASE) == (200, b"ok")
    monkeypatch.setattr(
        verifier,
        "build_opener",
        lambda *_: Opener(HTTPError(BASE, 404, "missing", {}, BytesIO(b"missing"))),
    )
    assert verifier.fetch(BASE) == (404, b"missing")
    monkeypatch.setattr(verifier, "build_opener", lambda *_: Opener(URLError("sentinel-secret")))
    with pytest.raises(verifier.VerificationError, match="network request failed"):
        verifier.fetch(BASE)
    monkeypatch.setattr(verifier, "build_opener", lambda *_: Opener(Response(b"x" * 2_000_001)))
    with pytest.raises(verifier.VerificationError, match="size limit"):
        verifier.fetch(BASE)
    assert (
        verifier.NoRedirects().redirect_request(None, None, 302, "", {}, "https://evil.example")
        is None
    )
