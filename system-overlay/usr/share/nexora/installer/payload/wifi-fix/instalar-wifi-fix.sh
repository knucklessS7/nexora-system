#!/bin/bash
set -eu
umask 077
BASE=/userdata/system/aura-wifi
SOURCE="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = --boot ] && [ -f "$BASE/disabled" ]; then exit 0; fi
command -v batocera-services >/dev/null || { echo "Execute dentro do Batocera 43."; exit 1; }
mkdir -p "$BASE" "$BASE/backups" /userdata/system/services
chmod 700 "$BASE" "$BASE/backups"
if [ -f /userdata/system/services/aura_wifi ] && ! grep -q '# aura-wifi-managed' /userdata/system/services/aura_wifi; then
  echo "Servico aura_wifi de outra origem preservado."; exit 1
fi
if [ ! -f "$BASE/backups/batocera.conf.original" ]; then
  cp -p /userdata/system/batocera.conf "$BASE/backups/batocera.conf.original"
  chmod 600 "$BASE/backups/batocera.conf.original"
fi
if [ "$SOURCE" != "$BASE" ]; then
  for F in wifi.py instalar-wifi-fix.sh verificar-wifi.sh desinstalar-wifi-fix.sh README.md; do
    if [ -f "$BASE/$F" ] && ! cmp -s "$SOURCE/$F" "$BASE/$F"; then cp -p "$BASE/$F" "$BASE/backups/$F.previous"; fi
    cp "$SOURCE/$F" "$BASE/$F"
  done
fi
chmod 700 "$BASE"/*.sh
rm -f "$BASE/disabled"
cat > /userdata/system/services/aura_wifi <<'SERVICE'
#!/bin/bash
# aura-wifi-managed
case "${1:-start}" in
 start) exec python3 /userdata/system/aura-wifi/wifi.py recover ;;
 stop) exit 0 ;;
 status) exec bash /userdata/system/aura-wifi/verificar-wifi.sh ;;
esac
SERVICE
chmod 700 /userdata/system/services/aura_wifi
batocera-services enable aura_wifi
# Native AutoConnect settings are applied through ConnMan. The boot service is
# necessary to reapply them if /var/lib/connman is volatile or regenerated.
exec python3 "$BASE/wifi.py" recover
