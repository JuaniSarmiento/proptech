# syntax=docker/dockerfile:1

FROM python:3.14.8-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev
COPY src ./src
COPY migraciones ./migraciones
COPY alembic.ini ./alembic.ini
RUN uv sync --locked --no-dev

FROM python:3.14.8-slim-trixie AS final
WORKDIR /app
RUN groupadd --system proptech && useradd --system --gid proptech --create-home proptech
COPY --from=build --chown=proptech:proptech /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER proptech
EXPOSE 8000
CMD ["uvicorn", "proptech_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
