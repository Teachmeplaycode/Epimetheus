FROM python:3.11-slim

LABEL org.opencontainers.image.title="epimetheus"
LABEL org.opencontainers.image.description="Epimetheus — a terminal companion who learns how humans talk"

WORKDIR /app

# Install only what's needed for runtime
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends tini

RUN groupadd -r epimetheus && useradd -r -g epimetheus epimetheus

COPY pyproject.toml .
COPY epimetheus/ epimetheus/

RUN pip install --no-cache-dir . && \
    pip cache purge

RUN mkdir -p /app/data && chown -R epimetheus:epimetheus /app

USER epimetheus

VOLUME ["/app/data"]
ENV DATA_DIR=/app/data

ENTRYPOINT ["tini", "--"]
CMD ["epimetheus", "crawl", "--source", "v2ex", "--max", "500", "--loop", "--loop-interval", "3600"]
