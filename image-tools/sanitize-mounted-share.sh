#!/usr/bin/env bash
set -euo pipefail

share=${1:?Uso: sanitize-mounted-share.sh /ponto/de/montagem/SHARE}
share=$(readlink -f -- "$share")
mountpoint -q "$share" || { echo 'O caminho precisa ser um ponto de montagem.' >&2; exit 1; }

safe_remove() {
  local target
  target=$(readlink -f -m -- "$1")
  case "$target" in "$share"/*) rm -rf -- "$target" ;; *) echo "Caminho inseguro: $target" >&2; exit 1 ;; esac
}

safe_remove "$share/system/connman"
safe_remove "$share/system/.config/NetworkManager"
safe_remove "$share/system/NetworkManager"
safe_remove "$share/system/batocera-smart-remote/state"
safe_remove "$share/system/batocera-smart-remote/logs"
safe_remove "$share/saves/flatpak/data/.var/app/com.google.Chrome/config/google-chrome"
safe_remove "$share/saves/flatpak/data/.var/app/com.google.Chrome/cache/google-chrome"

if [[ -d "$share/system/dynamic/store-apps" ]]; then
  while IFS= read -r -d '' profile; do safe_remove "$profile"; done < <(
    find "$share/system/dynamic/store-apps" -mindepth 2 -maxdepth 2 -type d \( -name profile -o -name chrome-profile \) -print0
  )
fi

if [[ -f "$share/system/batocera.conf" ]]; then
  sed -i -E '/^(wifi\.|network\.)/d' "$share/system/batocera.conf"
fi

find "$share/system" -type f \( -name '*.log' -o -name '*.old' -o -name '*.bak' -o -name '*.tmp' \) -delete
sync
