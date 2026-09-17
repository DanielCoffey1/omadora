#!/bin/bash
# Run as the test user after the actual installer has completed.
set -euo pipefail
export OMARCHY_PATH=/usr/local/share/omadora/upstream
export PATH="/usr/local/share/omadora/bin:$OMARCHY_PATH/bin:$PATH"
export XDG_RUNTIME_DIR
XDG_RUNTIME_DIR=$(mktemp -d)
chmod 0700 "$XDG_RUNTIME_DIR"
trap 'rm -rf -- "$XDG_RUNTIME_DIR"' EXIT
export XDG_CURRENT_DESKTOP=Hyprland
Hyprland --verify-config --config "$HOME/.config/hypr/hyprland.lua"
# Resolve every native Quickshell import used by the shipped desktop. This
# catches missing/new APIs without pretending to start a graphical session.
mkdir "$XDG_RUNTIME_DIR/qml-smoke"
python3 - "$XDG_RUNTIME_DIR/qml-smoke/shell.qml" <<'PY'
from pathlib import Path
import re
import sys
modules = set()
for path in Path('/usr/local/share/omadora/upstream/shell').rglob('*.qml'):
    for line in path.read_text().splitlines():
        match = re.match(r'import (Quickshell(?:\.[A-Za-z0-9]+)*)\b', line)
        if match:
            modules.add(match[1])
imports = '\n'.join(f'import {module} as M{i}' for i, module in enumerate(sorted(modules)))
Path(sys.argv[1]).write_text('import QtQuick\nimport Quickshell\n' + imports + '\nShellRoot {}\n')
print('Checking native imports:', ', '.join(sorted(modules)))
PY
status=0
QT_QPA_PLATFORM=offscreen timeout 5 quickshell -p "$XDG_RUNTIME_DIR/qml-smoke" >"$XDG_RUNTIME_DIR/qml.log" 2>&1 || status=$?
cat "$XDG_RUNTIME_DIR/qml.log"
# A successfully loaded ShellRoot stays alive; timeout is expected. A load
# failure exits earlier or never emits Configuration Loaded.
[[ $status == 124 ]]
grep -F 'Configuration Loaded' "$XDG_RUNTIME_DIR/qml.log"
if grep -E 'ERROR|Failed to load' "$XDG_RUNTIME_DIR/qml.log"; then exit 1; fi
echo 'PASS: Hyprland configuration and required Quickshell import modules.'
