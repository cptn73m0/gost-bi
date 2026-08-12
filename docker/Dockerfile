# syntax=docker/dockerfile:1
#
# GOST BI — Multi-platform Docker image
# Supported platforms: linux/amd64, linux/arm64 (Байкал/Эльбрус ARM)
# Runtime: Astra Linux SE 1.8 / Alt Linux 10+ / Windows 10-11 (via WSL2 or native)
#

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="GOST BI"
LABEL org.opencontainers.image.description="Российская BI-платформа с AI-ускорением"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.authors="GOST BI Contributors"
LABEL ru.gost-bi.target-platforms="Astra Linux SE 1.8, Alt Linux 10+, Windows 10/11"
LABEL ru.gost-bi.registry="Реестр отечественного ПО (заявка в процессе)"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    locales \
    fonts-dejavu-core \
    fonts-liberation \
    ca-certificates \
    && echo "ru_RU.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen ru_RU.UTF-8 \
    && update-locale LANG=ru_RU.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU:ru
ENV LC_ALL=ru_RU.UTF-8

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[dev]"

RUN groupadd -r gostbi && useradd -r -g gostbi -m -d /app gostbi \
    && chown -R gostbi:gostbi /app

RUN mkdir -p /home/gostbi/.superset && chown -R gostbi:gostbi /home/gostbi/.superset

USER gostbi

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8088/api/health || exit 1

CMD ["python", "-m", "uvicorn", "gost_bi.core.app:app", "--host", "0.0.0.0", "--port", "8088"]
