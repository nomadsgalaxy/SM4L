#!/usr/bin/env bash
# Run an unchanged SOLIDWORKS executable or installer in its own Proton prefix.
set -euo pipefail
if [[ "${1:-}" == --check ]]; then
  exec "${UMU_RUN:-umu-run}" --version
fi
exe="${1:-$(dirname -- "$(realpath -- "$0")")/sldworks.exe}"
if (( $# )); then shift; fi
[[ -f "$exe" ]] || { echo "Executable not found: $exe" >&2; exit 2; }
exe="$(realpath -- "$exe")"
state="${SOLIDWORKS_PROTON_STATE:-${XDG_DATA_HOME:-$HOME/.local/share}/solidworks-proton}"
# Refuse another CAD launch before starting a server or any helper.
case "$(basename -- "$exe")" in
  sldworks.exe|SWXDesktopLauncher.exe|ENOPLMCSAClient.exe)
    mkdir -p "$state"
    exec 9>"$state/cad-launch.lock"
    flock -n 9 || { echo "A SOLIDWORKS launch is already in progress." >&2; exit 1; }
    if pgrep -x sldworks.exe >/dev/null; then
      echo "SOLIDWORKS is already running. Close it before launching again." >&2
      exit 1
    fi
    ;;
esac
mkdir -p "$state/logs"
log_dir="$(mktemp -d "$state/logs/run-XXXXXX")"
export WINEPREFIX="$state/prefix" GAMEID=umu-default
# WebView2 bootstrap events need EVENT_MODIFY_STATE without SYNCHRONIZE.
export PROTON_NO_FSYNC="${PROTON_NO_FSYNC:-1}" PROTON_NO_ESYNC="${PROTON_NO_ESYNC:-1}"
# Pinned startup fixes are scoped to this dedicated prefix.
export PROTONPATH="${PROTONPATH:-UMU-Proton}"
server="$PROTONPATH/files/bin/wineserver"
[[ -x "$server" ]] || { echo "Set PROTONPATH to the installed Proton directory" >&2; exit 2; }
# A container-owned server cannot write memory in later containers' children.
# Start this prefix's persistent server on the host before UMU creates a container.
fsync=1; esync=1
if [[ "$PROTON_NO_FSYNC" == 1 ]]; then fsync=0; fi
if [[ "$PROTON_NO_ESYNC" == 1 ]]; then esync=0; fi
mkdir -p "$state/prefix/pfx"
# Match UMU's large descriptor budget for the shared server.
ulimit -n "$(ulimit -Hn)"
WINEPREFIX="$state/prefix/pfx" WINEFSYNC="$fsync" WINEESYNC="$esync" "$server" -p || { status=$?; [[ "$status" == 2 ]] || exit "$status"; }
if [[ "${SM4L_UI_COMPAT:-0}" == 1 ]]; then
  nohup python3 -B "$(dirname -- "$(realpath -- "$0")")/spacemouse.py" --ui-only >"$log_dir/ui-compat.log" 2>&1 </dev/null &
fi
# The CAD shortcut enables navigation after the host server is safely running.
if [[ "${SM4L_SPACEMOUSE:-0}" == 1 ]]; then
  nohup python3 -B "$(dirname -- "$(realpath -- "$0")")/spacemouse.py" >"$log_dir/spacemouse.log" 2>&1 </dev/null &
fi
export PROTON_LOG=1 PROTON_LOG_DIR="$log_dir"
cd -- "$(dirname -- "$exe")"
exec "${UMU_RUN:-umu-run}" "$exe" "$@"
