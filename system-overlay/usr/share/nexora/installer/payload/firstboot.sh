#!/bin/bash
set -u
BASE="/userdata/system/aura"
PAYLOAD="$BASE/payload"
STATE="$BASE/state"
LOG="$BASE/aura-firstboot.log"
LOCK="/tmp/aura-firstboot.lock"
INSTALL_STREAMING_APPS=0
[ -r "$PAYLOAD/nexora-defaults.conf" ] && . "$PAYLOAD/nexora-defaults.conf"
mkdir -p "$BASE" "$STATE"
if ! mkdir "$LOCK" 2>/dev/null; then exit 0; fi
trap 'python3 /userdata/system/aura-store-native/web_apps.py enforce-removed 2>/dev/null || true; rmdir "$LOCK" 2>/dev/null || true' EXIT
exec >>"$LOG" 2>&1

echo ""
echo "=================================================="
echo " NEXORA FIRST BOOT - $(date 2>/dev/null || true)"
echo "=================================================="
TOTAL_KB="$(df -Pk /userdata 2>/dev/null | awk 'NR==2 {print $2}')"; TOTAL_KB="${TOTAL_KB:-0}"
if [ "$TOTAL_KB" -lt 2000000 ] 2>/dev/null; then echo "[AGUARDANDO] SHARE ainda pequena (${TOTAL_KB} KB). Tenta novamente no proximo boot."; exit 0; fi
echo "[OK] SHARE pronta: ${TOTAL_KB} KB totais."
refresh_es(){
  # Preserve the Aura process/PATH; never restart the desktop after firstboot.
  if [ "$(curl -s --max-time 3 -o /dev/null -w '%{http_code}' http://127.0.0.1:1234/isIdle)" = 200 ]; then
    curl -fsS --max-time 5 http://127.0.0.1:1234/reloadgames >/dev/null || true
  else
    echo '[AURA] Interface ocupada; catalogo sera atualizado no retorno/proximo boot.'
  fi
}

if [ ! -f "$STATE/native-store-v70.done" ]; then
  echo "[1/5] Instalando Batocera Store Native offline..."
  NSRC="$PAYLOAD/native-store"; NDST="/userdata/system/aura-store-native"
  if [ -d "$NSRC" ] && command -v python3 >/dev/null 2>&1; then
    if [ -d "$NDST" ] && [ ! -d "$BASE/backups/native-store-before-v70" ]; then mkdir -p "$BASE/backups"; cp -a "$NDST" "$BASE/backups/native-store-before-v70"; fi
    mkdir -p "$NDST"; cp -R "$NSRC"/. "$NDST"/
    chmod +x "$NDST/launch.sh" "$NDST/install.py" 2>/dev/null || true
    if python3 "$NDST/install.py"; then touch "$STATE/native-store-v70.done"; echo "[OK] Store Native instalada; interface/catalogo funcionam offline."; refresh_es; else echo "[ERRO] Falha ao registrar Store Native em PORTS."; fi
  else echo "[ERRO] Payload Native ou Python ausente."; fi
fi

if [ ! -f "$STATE/theme.done" ]; then
  echo "[2/5] Preparando tema Aura..."
  THEME_DST="/userdata/themes/aura"; THEME_SRC=""
  for C in /usr/share/emulationstation/themes/es-theme-carbon /usr/share/emulationstation/themes/carbon /userdata/themes/es-theme-carbon; do [ -d "$C" ] && { THEME_SRC="$C"; break; }; done
  if [ -n "$THEME_SRC" ]; then
    rm -rf "$THEME_DST"; cp -a "$THEME_SRC" "$THEME_DST"; cp -f "$PAYLOAD/theme-aura-v4.2.xml" "$THEME_DST/theme.xml"
    SETTINGS="/userdata/system/configs/emulationstation/es_settings.cfg"
    if [ -f "$SETTINGS" ] && command -v python3 >/dev/null 2>&1; then
      python3 - "$SETTINGS" <<'PY2'
import sys,xml.etree.ElementTree as ET
p=sys.argv[1]
try:
 t=ET.parse(p);r=t.getroot();n=next((e for e in r.findall('string') if e.get('name')=='ThemeSet'),None)
 if n is None:n=ET.SubElement(r,'string',{'name':'ThemeSet'})
 n.set('value','aura');t.write(p,encoding='UTF-8',xml_declaration=True)
except Exception as e: print('[AVISO] tema:',e)
PY2
    fi
    touch "$STATE/theme.done"; refresh_es
  else echo "[AVISO] Tema Carbon base nao localizado."; fi
fi

# Streaming shortcuts are deliberately opt-in on a clean Nexora installation.
if [ "$INSTALL_STREAMING_APPS" = 1 ] && [ ! -f "$STATE/apps-streaming-v6.done" ]; then
  rm -f "$STATE/complete"
  if bash "$PAYLOAD/apps-completo-v1.0.sh"; then
    touch "$STATE/apps-streaming-v6.done"
    refresh_es
  else
    echo "[ERRO] Falha ao criar atalhos de streaming."
    exit 1
  fi
fi
if [ ! -f "$STATE/neon-v80.done" ]; then
  if bash "$PAYLOAD/install-neon.sh"; then refresh_es; else echo "[AURA NEON] Falha; confira o log. Tema anterior preservado."; fi
fi
if [ "$INSTALL_STREAMING_APPS" = 1 ]; then
  if python3 "$PAYLOAD/controller-update.py"; then
    if [ ! -f "$STATE/controller-v70.done" ]; then touch "$STATE/controller-v70.done"; refresh_es; fi
  else
    echo "[CONTROLE] Falha na atualizacao da navegacao."
  fi
fi
# Reconcile offline shortcuts before browser/network setup, including manual reinstalls.
if python3 /userdata/system/aura-store-native/reconcile.py; then
  if [ ! -f "$STATE/apps-layout-v64.done" ]; then touch "$STATE/apps-layout-v64.done"; refresh_es; fi
else
  echo "[AVISO] Organizacao APPS cancelada; confira gamelists e Flatpak."
fi
if [ "$INSTALL_STREAMING_APPS" = 1 ]; then
mkdir -p "$BASE/maintenance"
cat > "$BASE/maintenance/Aura - Reparar streaming.sh" <<'REPAIR'
#!/bin/bash
exec bash /userdata/system/aura/payload/repair-visible.sh
REPAIR
chmod +x "$BASE/maintenance/Aura - Reparar streaming.sh"
fi
# Network and Bluetooth are native Batocera settings. Nexora never rewrites them.
# A prior Aura helper could force one saved Wi-Fi profile at every reboot.
# Disable only that marked service; native Batocera profiles remain untouched.
if [ -f /userdata/system/services/aura_wifi ] && grep -q '# aura-wifi-managed' /userdata/system/services/aura_wifi; then
  batocera-services disable aura_wifi >/dev/null 2>&1 || true
  mkdir -p /userdata/system/aura-wifi
  : > /userdata/system/aura-wifi/disabled
  echo "[REDE] Serviço antigo de Wi-Fi desativado; usando as configurações salvas do Batocera."
fi
# Synchronize before HTTPS: an old RTC can otherwise block the network check.
echo "[HORA] Antes da sincronizacao: $(date)"
if command -v ntpd >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
  timeout 30 ntpd -q -p pool.ntp.org >>"$BASE/aura-ntp.log" 2>&1 || true
fi
echo "[HORA] Depois da sincronizacao: $(date)"
CAFILE="$PAYLOAD/ca-bundle.crt"
if [ -s "$CAFILE" ]; then
  export SSL_CERT_FILE="$CAFILE"
  export CURL_CA_BUNDLE="$CAFILE"
fi
if flatpak info --system com.google.Chrome >/dev/null 2>&1; then
  echo "[CHROME] Já instalado; nenhuma conexão é necessária nesta inicialização."
  ONLINE=2
else
echo "[REDE] Verificando internet para baixar o navegador (a Loja e o pareamento funcionam offline)..."
ONLINE=0
for I in $(seq 1 2); do
  if curl -fIsS --connect-timeout 5 --max-time 10 https://dl.flathub.org/repo/flathub.flatpakrepo >"$BASE/flathub-https.log" 2>&1; then ONLINE=1; break; fi
  if [ "$I" = 12 ] && command -v ntpd >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
    timeout 30 ntpd -q -p time.google.com >>"$BASE/aura-ntp.log" 2>&1 || true
  fi
  sleep 5
done
if [ "$ONLINE" -ne 1 ]; then
  echo "[OFFLINE] Loja e pareamento foram instalados. O Chrome será baixado automaticamente quando houver internet."
  sync; touch "$STATE/complete"; exit 0
fi
fi
if [ "$ONLINE" = 2 ]; then
  sync; touch "$STATE/complete"; exit 0
fi
echo "[OK] Internet detectada."
echo "[HORA] $(date 2>/dev/null || true)"
if ! command -v flatpak >/dev/null 2>&1; then echo "[ERRO] Flatpak ausente."; exit 0; fi
if ! flatpak remotes --system --columns=name 2>/dev/null | grep -qx 'flathub'; then
  echo "[FLATHUB] Configurando remote..."
  flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || { echo "[ERRO] Nao foi possivel configurar Flathub; tenta no proximo boot."; exit 1; }
fi
# Preserve installed applications and keys; normalize only the repository URL.
flatpak remote-modify --system --url=https://dl.flathub.org/repo/ flathub || exit 1
if [ -s "$CAFILE" ]; then
  python3 "$PAYLOAD/flathub-certificates.py" "$CAFILE" "$BASE/backups" || exit 1
fi
if ! flatpak remote-info --system flathub com.google.Chrome >"$BASE/flathub-check.log" 2>&1; then
  echo "[ERRO] Flatpak ainda nao consegue validar/acessar o Flathub. Data: $(date)"
  cat "$BASE/flathub-check.log"
  flatpak remotes --system --show-details
  exit 1
fi
# Explicit system scope matches the system Flathub remote.
for BROWSER in com.google.Chrome; do
  if ! flatpak info --system "$BROWSER" >/dev/null 2>&1; then
    OK=0
    for N in 1 2 3; do
      echo "[NAVEGADOR] $BROWSER tentativa $N/3"
      flatpak install --system -y --noninteractive flathub "$BROWSER" && { OK=1; break; }
      sleep 5
    done
    [ "$OK" -eq 1 ] || { echo "[ERRO] $BROWSER falhou. Verifique rede/espaco no log; tenta no proximo boot."; exit 1; }
  fi
done
# Remove the old browser only after Chrome was successfully installed.
if flatpak info --system com.google.Chrome >/dev/null 2>&1; then
  for OLD_SCOPE in --system --user; do
    if flatpak info "$OLD_SCOPE" org.chromium.Chromium >/dev/null 2>&1; then
      flatpak uninstall "$OLD_SCOPE" -y --noninteractive org.chromium.Chromium || { echo "[AVISO] Chromium ainda instalado; nova tentativa no proximo boot."; exit 1; }
    fi
  done
  python3 /userdata/system/aura-store-native/reconcile.py || true
fi
echo "[CHROME] Atalhos usam com.google.Chrome com perfis separados dos antigos."
echo "[DRM] Chrome inclui Widevine; reproducao ainda requer teste no aparelho."
if [ ! -f "$STATE/cursor.done" ]; then
  echo "[5/5] Aplicando cursor V1.2..."
  if bash "$PAYLOAD/cursor-v1.2.sh"; then touch "$STATE/cursor.done"; else echo "[AVISO] Cursor falhou; tenta no proximo boot."; exit 0; fi
fi
rm -f "/userdata/roms/ports/Aura - Instalar agora.sh" "/userdata/roms/ports/Batocera Store Native.sh" 2>/dev/null || true
sync; touch "$STATE/complete"
echo "[OK] BATOCERA AURA V6 STREAMING configurado por completo."
refresh_es
exit 0
