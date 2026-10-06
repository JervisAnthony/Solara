"""Opt-in, read-only deployment integrity checks. No recommendation/provider calls."""

import argparse
import json
import re
import sys
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ASSETS = (
    "travel-scopes.js",
    "inspiration.js",
    "selects.js",
    "app.js",
    "results.js",
    "itinerary.js",
    "feedback.js",
    "styles.css",
)
LOCAL_ASSETS = Path(__file__).resolve().parents[1] / "src/solara_travel/presentation/web/static"
MAX_RESPONSE_BYTES = 2_000_000


class VerificationError(Exception):
    """A safe operator-facing mismatch, without response bodies or credentials."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str) -> tuple[int, bytes]:
    """Bound each GET and refuse redirects, including cross-origin destinations."""
    request = Request(url, headers={"Accept-Encoding": "identity"})
    try:
        try:
            response = build_opener(NoRedirects()).open(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise VerificationError("response exceeds size limit")
            return response.code, body
    except (URLError, TimeoutError, OSError) as error:
        raise VerificationError("network request failed") from error


class FunctionalReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            self.urls.append(attributes.get("src", ""))
        elif tag == "link" and "stylesheet" in attributes.get("rel", "").split():
            self.urls.append(attributes.get("href", ""))


def _base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or (parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"))
    ):
        raise VerificationError("use an HTTPS service origin without credentials, path or query")
    try:
        _ = parsed.port
    except ValueError as error:
        raise VerificationError("invalid service port") from error
    return value.rstrip("/")


def _json(body: bytes) -> dict:
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError) as error:
        raise VerificationError("invalid operational JSON response") from error
    if not isinstance(value, dict):
        raise VerificationError("operational response must be an object")
    return value


def verify(base_url, expected_sha=None, *, get=fetch, assets_directory=LOCAL_ASSETS):
    """Verify eight exact assets against both live hashes and this local checkout."""
    base = _base_url(base_url)
    if expected_sha is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", expected_sha):
        raise VerificationError("expected SHA must be 40 hexadecimal characters")

    status, body = get(base + "/health")
    if status != 200 or _json(body) != {"status": "ok"}:
        raise VerificationError("health check mismatch")
    status, body = get(base + "/release")
    if status != 200:
        raise VerificationError("release endpoint unavailable")
    release = _json(body)
    if set(release) != {"product", "version", "source_revision"}:
        raise VerificationError("unexpected release metadata fields")
    if release["product"] != "Solara" or release["version"] != "0.1.0":
        raise VerificationError("release product/version mismatch")
    revision = release["source_revision"]
    if revision is not None and (
        not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision)
    ):
        raise VerificationError("invalid release revision")
    if expected_sha is not None and (revision is None or revision.lower() != expected_sha.lower()):
        raise VerificationError("deployed SHA mismatch")
    for path in ("/docs", "/redoc"):
        if get(base + path)[0] != 404:
            raise VerificationError("hosted API documentation must be disabled")

    status, body = get(base + "/")
    if status != 200:
        raise VerificationError("homepage unavailable")
    try:
        document = body.decode("utf-8")
    except UnicodeError as error:
        raise VerificationError("invalid homepage encoding") from error
    for identity in (
        "recommendation-form",
        "itinerary-studio",
        "export-trip-json",
        "export-trip-text",
    ):
        if f'id="{identity}"' not in document:
            raise VerificationError("MVP1 entrypoint missing")
    parser = FunctionalReferences()
    parser.feed(document)
    if len(parser.urls) != len(ASSETS):
        raise VerificationError("functional asset reference count mismatch")
    seen = set()
    for url in parser.urls:
        match = re.fullmatch(r"/static/([a-z-]+\.(?:js|css))\?v=([0-9a-f]{16})", url)
        if match is None or match[1] not in ASSETS or match[1] in seen:
            raise VerificationError("unversioned, duplicate or unsafe functional asset URL")
        name, fingerprint = match.groups()
        seen.add(name)
        status, content = get(base + url)
        if status != 200:
            raise VerificationError("functional asset unavailable")
        if sha256(content).hexdigest()[:16] != fingerprint:
            raise VerificationError("live asset fingerprint mismatch")
        try:
            local_content = (assets_directory / name).read_bytes()
        except OSError as error:
            raise VerificationError("local release asset unavailable") from error
        if content != local_content:
            raise VerificationError("live asset differs from checked-out release candidate")
    return release


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="HTTPS service origin")
    parser.add_argument("--expected-sha", help="exact pushed release-candidate commit")
    arguments = parser.parse_args(argv)
    try:
        release = verify(arguments.base_url, arguments.expected_sha)
    except (VerificationError, ValueError) as error:
        print(f"Release verification failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Release integrity verified: Solara {release['version']} · "
        f"revision {release['source_revision'] or 'unknown'} · 8 assets match checkout"
    )
    print("Provider acceptance remains a separate manual check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
