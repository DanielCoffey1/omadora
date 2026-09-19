#!/bin/bash
set -euo pipefail
if (( EUID == 0 )); then
  echo 'Run Omadora as your regular Fedora user, not with sudo.' >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo 'Omadora requires Fedora Workstation.' >&2
  exit 1
fi
. /etc/os-release
if [[ ${ID:-} != fedora || ${VARIANT_ID:-} != workstation || ${VERSION_ID:-} != 44 || -e /run/ostree-booted ]]; then
  echo 'This development release targets Fedora Workstation 44 (non-Atomic).' >&2
  exit 1
fi
command -v git >/dev/null || sudo dnf install -y git
command -v python3 >/dev/null || sudo dnf install -y python3
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
ref=${OMADORA_REF:-v0.2.2-alpha}
[[ $ref != -* ]] || { echo 'Invalid Omadora Git reference.' >&2; exit 1; }
git init "$stage/repo"
git -C "$stage/repo" remote add origin https://github.com/DanielCoffey1/omadora.git
git -C "$stage/repo" fetch --depth 1 origin "$ref"
git -C "$stage/repo" checkout --detach FETCH_HEAD
action=install
if [[ ${1:-} == upgrade || ${1:-} == recover || ${1:-} == rollback ]]; then
  action=$1
  shift
fi
if [[ $action == upgrade ]]; then
  python3 "$stage/repo/omadora.py" upgrade --local "$@"
else
  python3 "$stage/repo/omadora.py" "$action" "$@"
fi
