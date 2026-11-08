#!/usr/bin/env bash
# Install or update Pacioli as an always-on local service (systemd --user).
#
#   scripts/install-service.sh            # build, install units, (re)start
#   scripts/install-service.sh --uninstall
#
# Re-run it after pulling changes: it rebuilds the frontend, refreshes the
# backend dependencies and restarts the service. Data lives in
# ~/.local/share/pacioli (SQLite) and is never touched by this script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNITS=(pacioli.service pacioli-backup.service pacioli-backup.timer)

if [[ "${1:-}" == "--uninstall" ]]; then
  systemctl --user disable --now pacioli.service pacioli-backup.timer 2>/dev/null || true
  for unit in "${UNITS[@]}"; do rm -f "$UNIT_DIR/$unit"; done
  systemctl --user daemon-reload
  echo "Pacioli service removed. Data in ~/.local/share/pacioli was kept."
  exit 0
fi

echo "==> Backend dependencies"
if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  uv venv -q -p 3.12 "$ROOT/backend/.venv"
fi
VIRTUAL_ENV="$ROOT/backend/.venv" uv pip install -q -e "$ROOT/backend"

echo "==> Frontend build"
npm --prefix "$ROOT/frontend" ci --silent
npm --prefix "$ROOT/frontend" run -s build

echo "==> systemd units"
mkdir -p "$UNIT_DIR"
for unit in "${UNITS[@]}"; do cp "$ROOT/deploy/systemd/$unit" "$UNIT_DIR/$unit"; done
systemctl --user daemon-reload
systemctl --user enable pacioli.service pacioli-backup.timer
systemctl --user restart pacioli.service
systemctl --user start pacioli-backup.timer

echo "==> Health check"
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    echo "Pacioli is running at http://localhost:8000"
    exit 0
  fi
  sleep 1
done
echo "Pacioli did not answer; see: journalctl --user -u pacioli -n 50" >&2
exit 1
