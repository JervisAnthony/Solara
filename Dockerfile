FROM python:3.13-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels ".[web]"


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
        "solara-travel-ai[web]" \
    && rm -rf /wheels \
    && addgroup --system solara \
    && adduser --system --ingroup solara solara

USER solara

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/health\",timeout=5).read()"]

CMD ["python", "-m", "solara_travel.presentation.api.server"]
