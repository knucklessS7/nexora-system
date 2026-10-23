#!/bin/bash
set -eu
BASE=/userdata/system/aura-wifi
python3 "$BASE/wifi.py" diagnose
echo "--- Ultimos registros do ajuste (sem senha) ---"
tail -n 25 "$BASE/wifi.log"
