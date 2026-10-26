FROM ubuntu:24.04
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
RUN uv sync --locked --no-dev
