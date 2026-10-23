#!/usr/bin/env bash
set -euo pipefail

image=${1:?Uso: audit-image-privacy.sh IMAGEM.img}
boot_mount=$(mktemp -d)
share_mount=$(mktemp -d)
loopdev=""

cleanup() {
  mountpoint -q "$share_mount" && umount "$share_mount" || true
  mountpoint -q "$boot_mount" && umount "$boot_mount" || true
  [[ -z "$loopdev" ]] || losetup -d "$loopdev" 2>/dev/null || true
  rmdir "$boot_mount" "$share_mount" 2>/dev/null || true
}
trap cleanup EXIT

loopdev=$(losetup --find --show --partscan --read-only "$image")
mount -o ro "${loopdev}p1" "$boot_mount"
mount -o ro "${loopdev}p2" "$share_mount"

fail=0
check() {
  local label=$1
  shift
  local count
  count=$(find "$@" -type f -print 2>/dev/null | wc -l)
  printf '%-34s %s\n' "$label" "$count"
  [[ "$count" == 0 ]] || fail=1
}

check 'ConnMan/NetworkManager' "$share_mount/system/connman" "$share_mount/system/.config/NetworkManager"
check 'Perfis Chrome' "$share_mount/system/dynamic/store-apps" "$share_mount/saves/flatpak/data/.var/app/com.google.Chrome"
check 'Logs' "$share_mount/system/logs" "$share_mount/system/batocera-smart-remote/logs"
check 'Estado de pareamento' "$share_mount/system/batocera-smart-remote/state"

if [[ -f "$share_mount/system/batocera.conf" ]] && grep -Eq '^(wifi\.|network\.)' "$share_mount/system/batocera.conf"; then
  echo 'batocera.conf contém configuração de rede'
  fail=1
fi

if find "$share_mount/system" -type f \( -name 'id_rsa' -o -name 'id_ed25519' -o -name 'ssh_host_*_key' -o -name 'authorized_keys' \) -print -quit | grep -q .; then
  echo 'A imagem contém chaves SSH'
  fail=1
fi

exit "$fail"
