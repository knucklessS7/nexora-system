#!/bin/bash
# NEXORA USB COMBO RECOVERY — Realtek 8822BU / Bluetooth
# Does not alter saved Wi-Fi profiles, pairings, ROMs, or user configuration.
LOG=/userdata/system/nexora-usb-recovery.log
REPORT=/boot/NEXORA-USB-STATUS.txt
TMP=/tmp/nexora-usb-status.$$
mkdir -p /userdata/system 2>/dev/null || true
(
  echo "NEXORA USB STATUS"
  echo "Generated: $(date 2>/dev/null || true)"
  echo
  echo "[recovery]"
  sleep 4
  modprobe rtw88_8822bu 2>&1 || true
  modprobe btusb 2>&1 || true
  modprobe btrtl 2>&1 || true
  command -v rfkill >/dev/null 2>&1 && {
    rfkill unblock wifi || true
    rfkill unblock bluetooth || true
  }
  echo
  echo "[modules]"
  lsmod 2>/dev/null | grep -E 'rtw88|btusb|btrtl' || true
  echo
  echo "[radios]"
  command -v rfkill >/dev/null 2>&1 && rfkill list || true
  echo
  echo "[interfaces]"
  ip -br link 2>/dev/null || true
  echo
  echo "[usb-realtek]"
  command -v lsusb >/dev/null 2>&1 && lsusb | grep -Ei '0bda|realtek' || true
  echo
  echo "[kernel-last]"
  dmesg 2>/dev/null | grep -Ei 'rtw|8822|b82c|btusb|bluetooth|firmware' | tail -80 || true
) >"$TMP" 2>&1
cat "$TMP" >>"$LOG" 2>/dev/null || true
cp "$TMP" "$REPORT" 2>/dev/null || true
rm -f "$TMP"
exit 0