#!/bin/bash
set -euo pipefail
bash /src/iso/build-root.sh
bash /src/iso/pack.sh
bash /src/iso/make-iso.sh
