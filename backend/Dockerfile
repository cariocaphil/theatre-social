# Development-friendly image for the FastAPI backend.
#
# Dependencies come exclusively from pyproject.toml + uv.lock (uv sync),
# there is no requirements.txt. Source code is expected to be bind-mounted
# over /app by compose.yml for live-reload during development; this image
# also works standalone (e.g. `podman build` + `podman run`) since it COPYs
# the code in as a fallback baseline.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .
RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
