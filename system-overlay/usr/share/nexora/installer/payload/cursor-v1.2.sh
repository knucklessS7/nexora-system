#!/bin/bash
set -e
BASE="/userdata/system/dynamic/store-apps"
BACK="/userdata/system/dynamic-backup/cursor-fix-v1.2-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACK"

for F in "$BASE"/*/launch.sh; do
  [ -f "$F" ] || continue
  APP="$(basename "$(dirname "$F")")"
  mkdir -p "$BACK/$APP"
  cp -a "$F" "$BACK/$APP/launch.sh"

  sed -i '/cursor-show.sh/d' "$F"
  sed -i 's/ --ozone-platform=x11//g' "$F"

  if ! grep -q "Dynamic cursor v1.2" "$F"; then
    TMP="${F}.tmp"
    awk '
      NR==1 { print; next }
      !done && $0=="set -e" {
        print
        print "# Dynamic cursor v1.2"
        print "export DISPLAY=\"${DISPLAY:-:0}\""
        print "export XCURSOR_THEME=\"${XCURSOR_THEME:-Adwaita}\""
        print "export XCURSOR_SIZE=\"${XCURSOR_SIZE:-32}\""
        print "command -v unclutter >/dev/null 2>&1 && pkill -x unclutter >/dev/null 2>&1 || true"
        print "command -v xsetroot >/dev/null 2>&1 && xsetroot -cursor_name left_ptr >/dev/null 2>&1 || true"
        done=1
        next
      }
      { print }
    ' "$F" > "$TMP"
    mv "$TMP" "$F"
    chmod +x "$F"
  fi
done

sync
echo "[OK] Cursor V1.2 aplicado."
echo "Feche o aplicativo aberto e abra novamente."
