"""Offline operator-tool fixtures never contact Render or recommendation providers."""

import importlib.util
import json
import re
import subprocess
from hashlib import sha256
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
READ_GIT_ASSET = verifier.read_git_asset


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
    blobs = {
        path.split("/")[-1].split("?")[0]: content
        for path, (_, content) in responses.items()
        if path.startswith("/static/")
    }

    def read_git_asset(revision, name):
        assert revision == SHA
        return blobs[name]

    monkeypatch.setattr(verifier, "read_git_asset", read_git_asset)

    def get(url):
        assert url.startswith(BASE)
        path = url[len(BASE) :]
        assert path in responses, "unexpected provider-consuming or external request"
        calls.append(path)
        return responses[path]

    return responses, get, calls


def test_valid_release_verifies_release_blobs_without_provider_calls(operational_fixture):
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


@pytest.mark.parametrize("failure", ["missing", "hash", "git"])
def test_asset_content_mismatches_are_detected(operational_fixture, failure):
    responses, get, _ = operational_fixture
    url = next(path for path in responses if path.startswith("/static/travel-scopes.js"))
    if failure == "missing":
        responses[url] = 404, b"missing"
    elif failure == "hash":
        responses[url] = 200, b"wrong content"
    else:
        content = b"different live bytes\n"
        replacement = url.split("?v=")[0] + "?v=" + sha256(content).hexdigest()[:16]
        responses["/"] = 200, responses["/"][1].replace(url.encode(), replacement.encode())
        responses[replacement] = 200, content
    message = {
        "missing": "functional asset unavailable",
        "hash": "live asset fingerprint mismatch",
        "git": "live asset differs from deployed Git revision",
    }[failure]
    with pytest.raises(verifier.VerificationError, match=message):
        verifier.verify(BASE, SHA, get=get)


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
    output = capsys.readouterr().out
    assert SHA in output and "8 assets match release commit" in output
    monkeypatch.setattr(
        verifier, "verify", lambda *_args: {"version": "0.1.0", "source_revision": None}
    )
    assert verifier.main([BASE]) == 0
    output = capsys.readouterr().out
    assert "local worktree fallback; no authoritative Git revision" in output
    assert "match release commit" not in output

    def fail(*_args):
        raise verifier.VerificationError("deployed SHA mismatch")

    monkeypatch.setattr(verifier, "verify", fail)
    assert verifier.main([BASE]) == 1
    assert "deployed SHA mismatch" in capsys.readouterr().err


def test_real_git_blobs_succeed_despite_crlf_worktree(operational_fixture, monkeypatch, tmp_path):
    """Exercise real Git plumbing without modifying assets or creating commits."""
    responses, get, _ = operational_fixture
    revision = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=verifier.REPOSITORY_ROOT,
            capture_output=True,
            check=True,
            timeout=10,
        )
        .stdout.decode()
        .strip()
    )
    release = json.loads(responses["/release"][1])
    release["source_revision"] = revision
    responses["/release"] = 200, json.dumps(release).encode()
    for name in verifier.ASSETS:
        canonical = READ_GIT_ASSET(revision, name)
        assert b"\r\n" not in canonical and b"\n" in canonical
        (tmp_path / name).write_bytes(canonical.replace(b"\n", b"\r\n"))
        assert (tmp_path / name).read_bytes() != canonical
        old_url = next(path for path in responses if path.startswith(f"/static/{name}?"))
        url = f"/static/{name}?v={sha256(canonical).hexdigest()[:16]}"
        responses["/"] = 200, responses["/"][1].replace(old_url.encode(), url.encode())
        responses[url] = 200, canonical
    monkeypatch.setattr(verifier, "read_git_asset", READ_GIT_ASSET)
    assert verifier.verify(BASE, revision, get=get, assets_directory=tmp_path) == release


def test_returned_revision_selects_git_blobs_without_expected_sha(operational_fixture, monkeypatch):
    _, get, _ = operational_fixture
    original = verifier.read_git_asset
    calls = []

    def read(revision, name):
        calls.append((revision, name))
        return original(revision, name)

    monkeypatch.setattr(verifier, "read_git_asset", read)
    verifier.verify(BASE, get=get)
    assert calls == [(SHA, name) for name in verifier.ASSETS]


def test_sha_mismatch_precedes_git_reads_and_asset_requests(operational_fixture, monkeypatch):
    _, get, calls = operational_fixture
    monkeypatch.setattr(verifier, "read_git_asset", lambda *_: pytest.fail("must not read Git"))
    with pytest.raises(verifier.VerificationError, match="deployed SHA mismatch"):
        verifier.verify(BASE, "0" * 40, get=get)
    assert calls == ["/health", "/release"]


def test_null_revision_fallback_is_limited_and_byte_exact(
    operational_fixture, monkeypatch, tmp_path
):
    responses, get, _ = operational_fixture
    release = json.loads(responses["/release"][1])
    release["source_revision"] = None
    responses["/release"] = 200, json.dumps(release).encode()
    monkeypatch.setattr(verifier, "read_git_asset", lambda *_: pytest.fail("no revision"))
    verifier.verify(BASE, get=get, assets_directory=STATIC_DIRECTORY)
    (tmp_path / "travel-scopes.js").write_bytes(b"different bytes")
    with pytest.raises(verifier.VerificationError, match="differs from local worktree fallback"):
        verifier.verify(BASE, get=get, assets_directory=tmp_path)
    with pytest.raises(verifier.VerificationError, match="local worktree asset unavailable"):
        verifier.verify(BASE, get=get, assets_directory=tmp_path / "absent")


def test_git_reader_uses_requested_object_without_head_lookup(monkeypatch):
    calls = []

    def run(arguments, **kwargs):
        calls.append(arguments)
        assert arguments == ["git", "cat-file", "blob", f"{SHA}:{verifier.ASSET_PREFIX}/app.js"]
        assert kwargs == dict(
            cwd=verifier.REPOSITORY_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            check=True,
            timeout=10,
        )
        return subprocess.CompletedProcess(arguments, 0, stdout=b"canonical\n")

    monkeypatch.setattr(verifier.subprocess, "run", run)
    assert READ_GIT_ASSET(SHA.upper(), "app.js") == b"canonical\n"
    assert len(calls) == 1  # No HEAD check or branch change, even for an older object.


@pytest.mark.parametrize(
    "revision,name",
    [("HEAD", "app.js"), ("0" * 39, "app.js"), (SHA, "../secret"), (SHA, "unknown.js")],
)
def test_git_reader_rejects_untrusted_arguments(monkeypatch, revision, name):
    monkeypatch.setattr(verifier.subprocess, "run", lambda *_a, **_k: pytest.fail("unsafe call"))
    with pytest.raises(verifier.VerificationError, match="invalid release asset object request"):
        READ_GIT_ASSET(revision, name)


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("sentinel-secret /private/repo"),
        subprocess.CalledProcessError(128, "git", output=b"secret", stderr=b"/private/repo"),
        subprocess.TimeoutExpired("git", 10, output=b"secret", stderr=b"/private/repo"),
    ],
)
def test_git_failures_are_safe_in_verification_and_cli(
    operational_fixture, monkeypatch, capsys, error
):
    _, get, _ = operational_fixture

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(verifier.subprocess, "run", fail)
    monkeypatch.setattr(verifier, "read_git_asset", READ_GIT_ASSET)
    with pytest.raises(verifier.VerificationError, match="release Git asset unavailable") as result:
        verifier.verify(BASE, SHA, get=get)
    assert result.value.__suppress_context__
    monkeypatch.setattr(verifier, "verify", lambda *_: (_ for _ in ()).throw(result.value))
    assert verifier.main([BASE, "--expected-sha", SHA]) == 1
    output = capsys.readouterr().err
    assert "release Git asset unavailable" in output
    assert "secret" not in output and "/private/repo" not in output


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
