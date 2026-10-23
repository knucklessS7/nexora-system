#!/bin/bash
set -u
export PYTHONIOENCODING=utf-8
export SDL_VIDEO_CENTERED=1
cd /userdata/system/aura-store-native || exit 1
python3 reconcile.py >>/userdata/system/aura-store-native/reconcile.log 2>&1 || true
exec python3 neon.py
