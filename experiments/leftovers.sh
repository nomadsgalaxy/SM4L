#!/usr/bin/env bash
# Diagnostic only: list launcher-side processes that outlive their chain (no kill, no arguments printed).
# Run it before a launch that fails, or after a CAD crash, to see what a prefix restart would clear.
set -euo pipefail
cad=$(pgrep -x sldworks.exe | head -1 || true)
launcher=$(pgrep -x SWXDesktopLaunc | head -1 || true)
echo "sldworks.exe: ${cad:-none}   SWXDesktopLauncher: ${launcher:-none}"
ps -eo pid=,ppid=,etimes=,comm= | awk '$4 ~ /^(msedgewebview2|CATSTART|SWXDesktopLaunc|SLDEXITAPP|ENOPLMCSAClie|3DEXPERIENCELau)/ {printf "%-8s ppid %-8s %5ss  %s\n", $1, $2, $3, $4}'
if [[ -z "$cad" && -z "$launcher" ]]; then
  echo "No CAD or launcher chain is running: any msedgewebview2/CATSTART above is a leftover."
fi
