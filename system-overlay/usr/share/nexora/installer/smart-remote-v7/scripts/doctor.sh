#!/bin/bash
set -eu
cat /etc/os-release
uname -m
python3 - <<'PY'
import importlib.util,os,sys
mods=['aiohttp','evdev','qrcode','pygame']
missing=[m for m in mods if importlib.util.find_spec(m) is None]
print('Python:',sys.version)
print('Missing modules:',missing)
print('uinput writable:',os.access('/dev/uinput',os.W_OK))
if missing or not os.access('/dev/uinput',os.W_OK):sys.exit(1)
PY
command -v batocera-services
command -v xdotool || true
ip -4 -o addr show scope global
curl -fsS --max-time 3 http://127.0.0.1:1234/systems >/dev/null && echo 'ES loopback API: available' || echo 'ES app launching: unavailable'
