#!/bin/bash
set -eu
export DISPLAY=${DISPLAY:-:0}
exec python3 /userdata/system/batocera-smart-remote/scripts/local_panel.py
