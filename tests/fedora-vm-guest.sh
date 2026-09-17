#!/bin/bash
set -euo pipefail
mkdir -p /tmp/omadora-vm-results
exec > >(tee /tmp/omadora-vm-results/session.log) 2>&1
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
export OMARCHY_PATH=/usr/local/share/omadora/upstream
export PATH="/usr/local/share/omadora/bin:$OMARCHY_PATH/bin:$PATH"
# Software-rendered CI graphics can stall IPC while the first frames compile.
export OMARCHY_SHELL_IPC_TIMEOUT=10s
for ((attempt=0; attempt<60; attempt++)); do
  signature=$(hyprctl instances -j 2>/dev/null | jq -r '.[0].instance // empty') || true
  [[ -n ${signature:-} ]] && break
  sleep 3
done
[[ -n ${signature:-} ]]
export HYPRLAND_INSTANCE_SIGNATURE="$signature"
export WAYLAND_DISPLAY
WAYLAND_DISPLAY=$(hyprctl instances -j | jq -r '.[0].wl_socket')
sleep 20
timeout 30 grim /tmp/omadora-vm-results/desktop.png
for ((attempt=0; attempt<30; attempt++)); do
  if omarchy-shell shell ping; then break; fi
  sleep 2
done
errors=$(hyprctl configerrors)
printf '%s\n' "$errors"
[[ -z $errors || $errors == 'ok' ]]
hyprctl monitors -j
powerprofilesctl get
powerprofilesctl list
getenforce
test -z "${FONTCONFIG_FILE:-}"
fc-match -f '%{family[0]}' monospace | grep 'JetBrainsMonoNL Nerd Font'
gsettings get org.gnome.desktop.interface color-scheme | grep prefer-dark
gsettings get org.gnome.desktop.interface icon-theme
omarchy-menu toggle
sleep 2
timeout 30 grim /tmp/omadora-vm-results/menu.png
omarchy-menu toggle
network_action=$(jq -r '."setup.network".action' "$OMARCHY_PATH/default/omarchy/omarchy-menu.jsonc")
bash -c "$network_action"
sleep 1
timeout 30 grim /tmp/omadora-vm-results/network-panel.png
omarchy-shell shell hide omarchy.network
omarchy-launch-screensaver force
sleep 5
timeout 30 grim /tmp/omadora-vm-results/screensaver.png
sleep 15
timeout 30 grim /tmp/omadora-vm-results/screensaver-later.png
pkill -f '[o]rg.omarchy.screensaver' || true
echo 'PASS: desktop, menu and screensaver reached in booted VM.'
