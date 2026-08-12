#!/bin/bash
#
# GOST BI — Установка на Alt Linux (ALT Server/Workstation) 10+
#
# Требования: Alt Linux 10+, права root/sudo
# Совместимость: Alt Server, Alt Workstation, Simply Linux
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo "=== GOST BI — Установка на Alt Linux ==="
echo ""

if [ -f /etc/altlinux-release ]; then
    log "Обнаружен Alt Linux: $(cat /etc/altlinux-release)"
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Обнаружена ОС: $NAME $VERSION_ID"
fi

if [ "$(id -u)" -ne 0 ]; then
    err "Скрипт требует права root. Запустите: sudo bash install-alt.sh"
fi

log "Шаг 1/7: Обновление пакетов..."
apt-get update -qq

log "Шаг 2/7: Установка системных зависимостей..."
apt-get install -y -qq \
    python3.12 \
    python3.12-dev \
    python3-module-pip \
    python3-module-venv \
    postgresql16-client \
    redis \
    curl \
    git \
    gcc \
    gcc-c++ \
    libpq-devel \
    libssl-devel \
    libffi-devel \
    fonts-ttf-dejavu \
    fonts-ttf-liberation

log "Шаг 3/7: Настройка русской локали..."
localedef -i ru_RU -f UTF-8 ru_RU.UTF-8 2>/dev/null || true
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
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=GOST BI — Российская BI-платформа
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=gostbi
Group=gostbi
WorkingDirectory=/opt/gost-bi
Environment="PATH=/opt/gost-bi/venv/bin"
Environment="LANG=ru_RU.UTF-8"
ExecStart=/opt/gost-bi/venv/bin/uvicorn gost_bi.core.app:app --host 0.0.0.0 --port 8088
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

useradd -r -s /bin/false gostbi 2>/dev/null || true
chown -R gostbi:gostbi "$INSTALL_DIR"

systemctl daemon-reload
log "Служба создана: systemctl enable --now gost-bi"

echo ""
echo "=== Установка завершена ==="
echo ""
echo "Запуск:"
echo "  source $INSTALL_DIR/venv/bin/activate"
echo "  cd $INSTALL_DIR"
echo "  make check-all"
echo ""
echo "Адрес: http://localhost:8088/api/health"
