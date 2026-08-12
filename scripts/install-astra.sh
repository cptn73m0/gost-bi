#!/bin/bash
#
# GOST BI — Установка на Astra Linux (Special Edition) 1.8
#
# Требования: Astra Linux SE 1.8 (Смоленск), права root/sudo
# Совместимость: Astra Linux CE, Debian 12
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo "=== GOST BI — Установка на Astra Linux ==="
echo ""

# Проверка ОС
if [ -f /etc/astra_version ]; then
    ASTRA_VER=$(cat /etc/astra_version 2>/dev/null || echo "unknown")
    log "Обнаружена Astra Linux: $ASTRA_VER"
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Обнаружена ОС: $NAME $VERSION_ID"
else
    warn "Не удалось определить версию ОС"
fi

# Проверка прав
if [ "$(id -u)" -ne 0 ]; then
    err "Скрипт требует права root. Запустите: sudo bash install-astra.sh"
fi

log "Шаг 1/7: Обновление пакетов..."
apt-get update -qq

log "Шаг 2/7: Установка системных зависимостей..."
apt-get install -y -qq \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    postgresql-client-16 \
    redis-tools \
    curl \
    git \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    locales \
    fonts-dejavu \
    fonts-liberation

log "Шаг 3/7: Настройка русской локали..."
if ! locale -a | grep -q "ru_RU.utf8"; then
    echo "ru_RU.UTF-8 UTF-8" >> /etc/locale.gen
    locale-gen ru_RU.UTF-8
    update-locale LANG=ru_RU.UTF-8
fi
export LANG=ru_RU.UTF-8

log "Шаг 4/7: Создание виртуального окружения Python..."
INSTALL_DIR="${INSTALL_DIR:-/opt/gost-bi}"
mkdir -p "$INSTALL_DIR"
python3.12 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

log "Шаг 5/7: Установка GOST BI..."
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

log "Шаг 6/7: Проверка совместимости..."
python3 -c "
import sys, platform
print(f'  Python: {sys.version}')
print(f'  OS: {platform.platform()}')
print(f'  Arch: {platform.machine()}')
from gost_bi import __version__
print(f'  GOST BI: {__version__}')
print('  ✅ Совместимость подтверждена')
"

log "Шаг 7/7: Настройка автозапуска (systemd)..."
SERVICE_FILE="/etc/systemd/system/gost-bi.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GOST BI — Российская BI-платформа
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=gostbi
Group=gostbi
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="LANG=ru_RU.UTF-8"
Environment="DATABASE_URL=postgresql://gostbi:gostbi@localhost:5432/gostbi"
Environment="REDIS_URL=redis://localhost:6379/0"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn gost_bi.core.app:app --host 0.0.0.0 --port 8088
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

useradd -r -s /bin/false gostbi 2>/dev/null || true
chown -R gostbi:gostbi "$INSTALL_DIR"

systemctl daemon-reload
log "Служба GOST BI создана: systemctl enable --now gost-bi"

echo ""
echo "=== Установка завершена ==="
echo ""
echo "Запуск:"
echo "  source $INSTALL_DIR/venv/bin/activate"
echo "  cd $INSTALL_DIR"
echo "  make check-all"
echo ""
echo "Запуск как служба:"
echo "  systemctl start gost-bi"
echo "  systemctl status gost-bi"
echo ""
echo "Проверка:"
echo "  curl http://localhost:8088/api/health"
