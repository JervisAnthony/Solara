"""Privacy-conscious one-process Uvicorn entrypoint for hosted Solara."""

import os
from collections.abc import Mapping

import uvicorn

from solara_travel.config import DeploymentConfigurationError

_FACTORY = "solara_travel.presentation.api.deployment:create_deployment_app"


def load_port(environ: Mapping[str, str] | None = None) -> int:
    """Parse the hosting platform's port without reading unrelated settings."""

    source = os.environ if environ is None else environ
    raw = source.get("PORT", "8000")
    if not isinstance(raw, str):
        raise DeploymentConfigurationError("PORT must be an integer between 1 and 65535")
    try:
        port = int(raw.strip())
    except ValueError as exc:
        raise DeploymentConfigurationError("PORT must be an integer between 1 and 65535") from exc
    if not 1 <= port <= 65_535:
        raise DeploymentConfigurationError("PORT must be an integer between 1 and 65535")
    return port


def main() -> None:
    """Run the deployment factory with a single privacy-safe worker."""

    uvicorn.run(
        _FACTORY,
        host="0.0.0.0",
        port=load_port(),
        workers=1,
        factory=True,
        proxy_headers=False,
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
