#!/bin/bash
set -euo pipefail
mkdir -p /tmp/omadora-vm-results
exec > >(tee /tmp/omadora-vm-results/session.log) 2>&1
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
export OMARCHY_PATH=/usr/local/share/omadora/upstream
export PATH="/usr/local/share/omadora/bin:$OMARCHY_PATH/bin:$PATH"
for ((attempt=0; attempt<60; attempt++)); do
  signature=$(hyprctl instances -j 2>/dev/null | jq -r '.[0].instance // empty') || true
  [[ -n ${signature:-} ]] && break
  sleep 3
done
[[ -n ${signature:-} ]]
export HYPRLAND_INSTANCE_SIGNATURE="$signature"
export WAYLAND_DISPLAY
WAYLAND_DISPLAY=$(hyprctl instances -j | jq -r '.[0].wl_socket')
for ((attempt=0; attempt<30; attempt++)); do
  if omarchy-shell shell ping; then break; fi
  sleep 2
done
omarchy-shell shell ping
errors=$(hyprctl configerrors)
printf '%s\n' "$errors"
[[ -z $errors || $errors == 'ok' ]]
hyprctl monitors -j
sleep 3
grim /tmp/omadora-vm-results/desktop.png
omarchy-menu toggle
sleep 2
grim /tmp/omadora-vm-results/menu.png
omarchy-menu toggle
omarchy-launch-screensaver force
sleep 5
grim /tmp/omadora-vm-results/screensaver.png
pkill -f '[o]rg.omarchy.screensaver' || true
echo 'PASS: desktop, menu and screensaver reached in booted VM.'
