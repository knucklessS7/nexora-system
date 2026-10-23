#!/bin/bash
# AURA STREAMING APP RUNTIME V4 DISPATCHER
# No persistent Python wrapper; Chrome still handles web UI/DRM/playback.
exec bash /userdata/system/aura/streaming-native-v4/launch.sh "$@"
