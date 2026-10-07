#!/usr/bin/env bash
# Route this Proton prefix's browser links to its authenticated Windows Firefox profile.
set -euo pipefail
[[ $# == 1 ]] || { echo "Expected one browser URL" >&2; exit 2; }
state="${SOLIDWORKS_PROTON_STATE:-$HOME/.local/share/solidworks-proton}"
client="$HOME/.local/share/umu/steamrt3/pressure-vessel/bin/steam-runtime-launch-client"
[[ -f "$state/browser-windows-firefox/user.js" ]] || { echo "Run launch_windows_browser.py first" >&2; exit 2; }
exec "$client" --host -- /usr/bin/firefox --profile "$state/browser-windows-firefox" --new-tab "$1"
