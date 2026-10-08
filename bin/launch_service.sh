#!/usr/bin/env bash
# Boot the prefix's 3DEXPERIENCE Launcher tray so the browser's Open button has something
# to talk to (127.0.0.1:20250). Meant for a login unit; it never starts CAD or takes the CAD lock.
set -euo pipefail
root="$(dirname -- "$(realpath -- "$0")")"
# XAUTHORITY changes whenever KWin restarts, so take the display variables from the live session.
while IFS== read -r key value; do
  case "$key" in DISPLAY|WAYLAND_DISPLAY|XAUTHORITY) export "$key=$value" ;; esac
done < <(systemctl --user show-environment)
if curl -s -m 2 -o /dev/null http://127.0.0.1:20250/; then exit 0; fi
export SOLIDWORKS_PROTON_STATE="${SOLIDWORKS_PROTON_STATE:-${XDG_DATA_HOME:-$HOME/.local/share}/solidworks-proton}"
export PROTONPATH="${PROTONPATH:-$HOME/.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4}"
# The bridge units own the add-in loaders; don't spawn duplicates from here.
export SM4L_UI_COMPAT=0 SM4L_SPACEMOUSE=0
export PROTON_USE_XALIA=0 PROTON_VERB=run WINEDEBUG="${WINEDEBUG:--all}"
if [[ -z "${UMU_RUN:-}" && -x "$HOME/.local/bin/umu-run" ]]; then export UMU_RUN="$HOME/.local/bin/umu-run"; fi
tray="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/3DEXPERIENCE Launcher/3DEXPERIENCELauncherSysTray.exe"
exec "$root/launch_proton.sh" "$tray"
