#!/bin/bash
set -eu
ID="${1:-}"
case "$ID" in
  prime) URL=https://www.primevideo.com/ ;;
  netflix) URL=https://www.netflix.com/browse ;;
  disney) URL=https://www.disneyplus.com/ ;;
  globoplay) URL=https://globoplay.globo.com/ ;;
  spotify) URL=https://open.spotify.com/ ;;
  apple_music) URL=https://music.apple.com/br/new ;;
  deezer) URL=https://www.deezer.com/br/ ;;
  youtube) URL=https://www.youtube.com/tv ;;
  youtube_music) URL=https://music.youtube.com/ ;;
  # AURA expanded catalog v1
  appletv) URL=https://tv.apple.com/br ;;
  paramount) URL=https://www.paramountplus.com/br/ ;;
  mubi) URL=https://mubi.com/pt ;;
  viki) URL=https://www.viki.com/ ;;
  pluto) URL=https://pluto.tv/br/ ;;
  looke) URL=https://www.looke.com.br/ ;;
  belasartes) URL=https://www.belasartesalacarte.com.br/ ;;
  curiosity) URL=https://curiositystream.com/ ;;
  nebula) URL=https://nebula.tv/ ;;
  wetv) URL=https://wetv.vip/ ;;
  iqiyi) URL=https://www.iq.com/ ;;
  kocowa) URL=https://www.kocowa.com/ ;;
  bandplay) URL=https://bandplay.com/ ;;
  sbt) URL=https://mais.sbt.com.br/ ;;
  twitch) URL=https://www.twitch.tv/ ;;
  kick) URL=https://kick.com/ ;;
  dailymotion) URL=https://www.dailymotion.com/ ;;
  vimeo) URL=https://vimeo.com/ ;;
  amazonmusic) URL=https://music.amazon.com.br/ ;;
  soundcloud) URL=https://soundcloud.com/ ;;
  tunein) URL=https://tunein.com/ ;;
  radiogarden) URL=https://radio.garden/ ;;
  mixcloud) URL=https://www.mixcloud.com/ ;;
  nasa) URL=https://plus.nasa.gov/ ;;
  ted) URL=https://www.ted.com/ ;;
  khan) URL=https://pt.khanacademy.org/ ;;
  dazn) URL=https://www.dazn.com/pt-BR/home ;;
  f1tv) URL=https://f1tv.formula1.com/ ;;
  fifa) URL=https://www.plus.fifa.com/ ;;
  xboxcloud) URL=https://www.xbox.com/pt-BR/play ;;
  geforcenow) URL=https://play.geforcenow.com/ ;;
  airconsole) URL=https://www.airconsole.com/ ;;
  photopea) URL=https://www.photopea.com/ ;;
  archive) URL=https://archive.org/ ;;
  # AURA expanded catalog v1
  rtp) URL=https://www.rtp.pt/play/ ;;
  nhk) URL=https://www3.nhk.or.jp/nhkworld/ ;;
  dw) URL=https://www.dw.com/ ;;
  aljazeera) URL=https://www.aljazeera.com/live ;;
  euronews) URL=https://www.euronews.com/ ;;
  mytuner) URL=https://mytuner-radio.com/ ;;
  qobuz) URL=https://play.qobuz.com/ ;;
  duolingo) URL=https://www.duolingo.com/ ;;
  coursera) URL=https://www.coursera.org/ ;;
  windy) URL=https://www.windy.com/ ;;
  openstreetmap) URL=https://www.openstreetmap.org/ ;;
  hbomax) URL=https://www.hbomax.com/ ;;
  *) echo "Aplicativo desconhecido: $ID"; exit 2 ;;
esac
AURA_DRM_MODE="${2:-}"
case "$AURA_DRM_MODE" in
  components) URL=chrome://components/ ;;
  settings) URL=chrome://settings/content/protectedContent ;;
  "") ;;
  *) echo "Modo desconhecido"; exit 2 ;;
esac
BASE=/userdata/system/dynamic/store-apps/$ID
LOGDIR=/userdata/system/aura/logs
mkdir -p "$BASE" "$LOGDIR"
exec >>"$LOGDIR/streaming-$ID.log" 2>&1
echo "--- $(date) $ID ---"
export DISPLAY="${DISPLAY:-:0}"
export XCURSOR_THEME="${XCURSOR_THEME:-Adwaita}"
export XCURSOR_SIZE="${XCURSOR_SIZE:-32}"
show_error() {
  # Error dialogs must not retain the streaming lock.
  exec 9>&-
  local message="$1"
  local report="$LOGDIR/erro-$ID.txt"
  {
    printf '%s\n\n' "$message"
    echo "Fotografe esta tela. Feche a janela para voltar ao menu."
    echo "--- Ultima tentativa ---"
    tail -n 35 "$LOGDIR/streaming-$ID.log" 2>/dev/null || true
    if [ "${2:-}" = install ]; then
      echo "--- Instalacao dos navegadores ---"
      tail -n 25 /userdata/system/aura/aura-firstboot.log 2>/dev/null || true
    fi
  } > "$report"
  if command -v xterm >/dev/null 2>&1; then
    xterm -hold -title "Aura - erro ao abrir streaming" -geometry 110x30 -e cat "$report" || true
  elif command -v zenity >/dev/null 2>&1; then
    zenity --text-info --title="Aura - erro ao abrir streaming" --width=900 --height=600 --filename="$report" || true
  elif command -v xmessage >/dev/null 2>&1; then
    xmessage -center -file "$report" || true
  fi
}
pkill -x unclutter >/dev/null 2>&1 || true
xsetroot -cursor_name left_ptr >/dev/null 2>&1 || true
APP=com.google.Chrome
PROFILE="$BASE/chrome-profile"
exec 9>/tmp/aura-streaming.lock
flock -n 9 || { show_error "Outro streaming esta aberto. Feche-o antes de abrir este."; exit 1; }
EXTRA=()
WINDOW_ARGS=(--start-maximized)
# YouTube Leanback uses its own remote-control navigation.
if [ "$ID" = youtube ] && [ -z "$AURA_DRM_MODE" ]; then
  WINDOW_ARGS=(--kiosk)
  EXTRA+=("--user-agent=Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/531.2+ (KHTML, Like Gecko) WebBrowser/1.0 SmartTV Safari/531.2+")
fi
# Batocera starts PORTS as root. Chromium refuses root without this option.
# The outer Flatpak isolation is still used.
# Suppress startup infobars in this dedicated launcher, as requested.
# This does NOT restore Chromium sandboxing; the existing root option remains.
if [ "$(id -u)" -eq 0 ]; then EXTRA+=(--no-sandbox --test-type); fi
EXTRA+=(--remote-debugging-address=127.0.0.1 --remote-debugging-port=0 --disable-background-mode --no-default-browser-check --disable-session-crashed-bubble --hide-crash-restore-bubble --noerrdialogs --disable-infobars)
# Match Batocera's native Flatpak generator: default installation lookup.
# An info failure is diagnostic only; it must never prevent a real launch.
echo "[AURA 7.1] Abrindo Chrome pelo resolvedor nativo Flatpak."
# AURA V4: flatpak run valida Chrome; sem consulta info redundante.
export SDL_JOYSTICK_HIDAPI_XBOX=0
# Directory required by Batocera's own batocera-flatpak-update.
mkdir -p /userdata/saves/flatpak/data/.cache/.flatpak-helper/monitor
# Install corrections even after an app was reinstalled by the Store.
PAYLOAD=/userdata/system/aura/payload
# AURA STREAMING APP RUNTIME V4: lightweight, short-lived native preflight.
# Navigation/DRM/playback and all Chrome flags below are left untouched.
V4_RUNTIME=/userdata/system/aura/streaming-native-v4/runtime.py
if [ -f "$V4_RUNTIME" ]; then
  if ! python3 "$V4_RUNTIME" prepare "$ID" "$PROFILE" "$PAYLOAD"; then
    echo "[AURA V4] Aviso: preflight falhou; usando preparacao original."
    python3 "$PAYLOAD/controller-update.py" || true
    python3 "$PAYLOAD/streaming-drm.py" "$PROFILE" || true
  fi
else
  echo "[AURA V4] Runtime ausente; usando preparacao original."
  python3 "$PAYLOAD/controller-update.py" || true
  python3 "$PAYLOAD/streaming-drm.py" "$PROFILE" || true
fi
BRIDGE_PID=""
NAV_PID=""
HEALTH_PID=""
READY="$(mktemp /tmp/aura-controller.XXXXXX)"
rm -f "$READY"
stop_helper() {
  local pid="${1:-}"
  [ -n "$pid" ] || return 0
  kill "$pid" 2>/dev/null || true
  for attempt in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep .1
  done
  if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid" 2>/dev/null || true; fi
  wait "$pid" 2>/dev/null || true
}
cleanup_controller() {
  if [ -n "$HEALTH_PID" ]; then stop_helper "$HEALTH_PID"; HEALTH_PID=""; fi
  if [ -n "$NAV_PID" ]; then stop_helper "$NAV_PID"; fi
  if [ -n "$BRIDGE_PID" ]; then stop_helper "$BRIDGE_PID"; fi
  rm -f "$READY"
}
trap 'if declare -F stop_splash >/dev/null 2>&1; then stop_splash; fi; cleanup_controller' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [ "${AURA_STREAMING_HEALTH:-0}" = "1" ] && [ -f "$PAYLOAD/streaming-health.py" ]; then
  python3 -u "$PAYLOAD/streaming-health.py" "$$" "$ID" 9>&- &
  HEALTH_PID=$!
fi
AURA_PAD_MODE=false
if [ -f "$PAYLOAD/controller-bridge.py" ]; then
  python3 -u "$PAYLOAD/controller-bridge.py" "$READY" 9>&- &
  BRIDGE_PID=$!
  for I in $(seq 1 30); do
    if [ -f "$READY" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; then AURA_PAD_MODE=true; break; fi
    kill -0 "$BRIDGE_PID" 2>/dev/null || break
    sleep .1
  done
fi
if [ "$AURA_PAD_MODE" = false ] && [ -n "$BRIDGE_PID" ]; then
  stop_helper "$BRIDGE_PID"
  BRIDGE_PID=""
fi
if [ -d "$BASE/extension" ]; then
  printf 'globalThis.AURA_NATIVE_CONTROLLER = %s;\n' "$AURA_PAD_MODE" > "$BASE/extension/controller-mode.js"
fi
echo "[CONTROLE] Mapeamento nativo ativo: $AURA_PAD_MODE (A=confirmar, B=voltar)"
# Chrome profiles are separate; old Chromium login files remain untouched.
rm -f "$PROFILE/DevToolsActivePort"
python3 -u "$PAYLOAD/chrome-navigation.py" "$PROFILE" 9>&- &
NAV_PID=$!

# AURA STREAMING STARTUP SPLASH V5
# Overlay native X11 no processo separado; falha nao bloqueia os aplicativos.
SPLASH_PID=""
stop_splash() {
  if [ -n "$SPLASH_PID" ]; then
    kill "$SPLASH_PID" 2>/dev/null || true
    wait "$SPLASH_PID" 2>/dev/null || true
    SPLASH_PID=""
  fi
}
if [ "${AURA_SPLASH:-1}" != "0" ] && [ -f /userdata/system/aura/streaming-native-v5/splash.py ]; then
  python3 -u /userdata/system/aura/streaming-native-v5/splash.py "$ID" "$PROFILE" "$$" 9>&- &
  SPLASH_PID=$!
fi

# Google Chrome bundles its Widevine; verify actual playback on the device.
if flatpak run -v "--filesystem=$BASE:rw" "$APP" \
  "--user-data-dir=$PROFILE" --no-first-run "${WINDOW_ARGS[@]}" --ozone-platform=x11 \
  --disable-features=Translate,TranslateUI --lang=pt-BR \
  "${EXTRA[@]}" "--app=$URL" 9>&-; then
  exit 0
else
  RC=$?
  echo "[ERRO] $APP encerrou com codigo $RC."
  stop_splash
  cleanup_controller
  show_error "O Chrome nao iniciou pelo Aura (codigo $RC). Veja o erro real abaixo."
  exit "$RC"
fi
