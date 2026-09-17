#!/bin/bash
# Session environment for SSH-driven tests in the disposable VM.
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
export OMARCHY_PATH=/usr/local/share/omadora/upstream
export PATH="/usr/local/share/omadora/bin:$OMARCHY_PATH/bin:$PATH"
export OMARCHY_SHELL_IPC_TIMEOUT=10s
export HYPRLAND_INSTANCE_SIGNATURE
HYPRLAND_INSTANCE_SIGNATURE=$(hyprctl instances -j | jq -r '.[0].instance')
export WAYLAND_DISPLAY
WAYLAND_DISPLAY=$(hyprctl instances -j | jq -r '.[0].wl_socket')
