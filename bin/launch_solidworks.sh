#!/usr/bin/env bash
# Start the installed CAD application with the working isolated Proton settings.
set -euo pipefail
root="$(dirname -- "$(realpath -- "$0")")"
export SOLIDWORKS_PROTON_STATE="${SOLIDWORKS_PROTON_STATE:-${XDG_DATA_HOME:-$HOME/.local/share}/solidworks-proton}"
export PROTONPATH="${PROTONPATH:-$HOME/.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4}"
export SM4L_UI_COMPAT="${SM4L_UI_COMPAT:-1}"
export SM4L_SPACEMOUSE="${SM4L_SPACEMOUSE:-1}"
export PROTON_USE_XALIA=0 PROTON_VERB=run WINEDEBUG="${WINEDEBUG:--all}"
if [[ -z "${UMU_RUN:-}" && -x "$HOME/.local/bin/umu-run" ]]; then export UMU_RUN="$HOME/.local/bin/umu-run"; fi
cad="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS/sldworks.exe"
exec "$root/launch_proton.sh" "$cad" "$@"
