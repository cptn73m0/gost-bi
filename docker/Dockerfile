# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="GOST BI"
LABEL org.opencontainers.image.description="Российская BI-платформа с AI-ускорением"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[dev]"

RUN groupadd -r gostbi && useradd -r -g gostbi -d /app gostbi \
    && chown -R gostbi:gostbi /app

USER gostbi

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8088/api/health || exit 1

CMD ["uvicorn", "gost_bi.core.app:app", "--host", "0.0.0.0", "--port", "8088"]
