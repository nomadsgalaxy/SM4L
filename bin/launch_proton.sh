#!/usr/bin/env bash
# Run an unchanged SOLIDWORKS executable or installer in its own Proton prefix.
set -euo pipefail
if [[ "${1:-}" == --check ]]; then
  exec "${UMU_RUN:-umu-run}" --version
fi
# --oneshot: for short setup commands (for example "cmd.exe /c exit 0" that creates the prefix, or a registry tool). It does not
# leave a persistent wineserver behind, so Proton's launcher returns when the program exits, with the program's exit code.
# When a wineserver already serves the prefix it runs the program with Proton's own wine64 against that server instead,
# which also returns the exit code. Not for CAD or its launcher.
oneshot=0
if [[ "${1:-}" == --oneshot ]]; then oneshot=1; shift; fi
exe="${1:-$(dirname -- "$(realpath -- "$0")")/sldworks.exe}"
if (( $# )); then shift; fi
[[ -f "$exe" ]] || { echo "Executable not found: $exe" >&2; exit 2; }
exe="$(realpath -- "$exe")"
state="${SOLIDWORKS_PROTON_STATE:-${XDG_DATA_HOME:-$HOME/.local/share}/solidworks-proton}"
# Refuse another CAD launch before starting a server or any helper.
case "$(basename -- "$exe")" in
  sldworks.exe|SWXDesktopLauncher.exe|ENOPLMCSAClient.exe)
    mkdir -p "$state"
    exec 9>"$state/cad-run.lock"
    flock -n 9 || { echo "A SOLIDWORKS launch is already in progress." >&2; exit 1; }
    if pgrep -x sldworks.exe >/dev/null; then
      echo "SOLIDWORKS is already running. Close it before launching again." >&2
      exit 1
    fi
    # Vendor clients stay alive after authentication; only CAD owns the run lock.
    [[ "$exe" == */sldworks.exe ]] || exec 9>&-
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
# A fresh prefix must be created WITHOUT the persistent host server: that server would load an empty registry while Proton copies
# its default registry in, and then overwrite the copy with its own tiny one when it exits (a prefix without CLSID or Uninstall
# keys, where installers fail with status 5). So when the registry is missing or trivial (no CLSID keys), create the prefix first
# with a plain umu-run, wait for its server to exit, and only then start the persistent one. (--oneshot never starts the
# persistent server, so its own umu-run creates the prefix.)
# Ready = the CLSID keys are there AND the registry has a healthy number of keys: a fresh prefix from Proton's default registry has
# about 17,000 keys, one clobbered by an early server about 80 (SM4L_MIN_REG_KEYS overrides the minimum of 5000, for tests).
prefix_ready() {
  local reg="$state/prefix/pfx/system.reg"
  [[ -f "$reg" ]] && grep -q -a -F '[Software\\Classes\\CLSID\\' "$reg" && (( $(grep -c -a '^\[' "$reg") >= ${SM4L_MIN_REG_KEYS:-5000} ))
}
# A fresh UMU-Proton prefix has no Desktop folder (or Documents, Downloads, ...) in its user profile. CAD's Open and Save dialogs then
# fail in SHGetDesktopFolder and the process crashes (c0000005 in comdlg32), so make the standard profile folders if they are missing.
# Existing entries, including symlinks, are left alone.
ensure_profile_folders() {
  local users="$state/prefix/pfx/drive_c/users" entry
  [[ -d "$users" ]] || return 0
  for entry in steamuser/Desktop steamuser/Documents steamuser/Downloads steamuser/Pictures steamuser/Music steamuser/Videos Public/Desktop Public/Documents; do
    if [[ ! -e "$users/$entry" && ! -L "$users/$entry" ]]; then mkdir -p -- "$users/$entry" || true; fi
  done
}
if (( ! oneshot )) && ! prefix_ready; then
  echo "Creating the Proton prefix (plain umu-run, no persistent server yet)..." >&2
  ( cd -- "$state" && "${UMU_RUN:-umu-run}" "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0 9>&- ) || true
  WINEPREFIX="$state/prefix/pfx" timeout 60 "$server" -w 9>&- || true
  prefix_ready || { echo "The prefix was not initialised (no healthy registry with CLSID keys in $state/prefix/pfx/system.reg); not starting a server on it." >&2; exit 3; }
fi
if (( ! oneshot )); then ensure_profile_folders; fi
# Classic (unthemed) painting is the fix for the missing checkbox/radio labels; put it back if a Proton
# or Wine update reset it. Only edits user.reg while no wineserver runs for this prefix.
sm4l_root="$(realpath -- "$(dirname -- "$(realpath -- "$0")")/..")"
python3 -I "$sm4l_root/setup/ensure_theme_off.py" "$state/prefix/pfx" || true
if (( oneshot )); then
  case "$(basename -- "$exe")" in sldworks.exe|SWXDesktopLauncher.exe|ENOPLMCSAClient.exe)
    echo "--oneshot is for short setup commands, not for CAD or its launcher" >&2; exit 2 ;;
  esac
  ensure_profile_folders
  if python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); from ensure_theme_off import server_running; sys.exit(0 if server_running(sys.argv[2]) else 1)' "$sm4l_root/setup" "$state/prefix/pfx"; then
    export WINEPREFIX="$state/prefix/pfx" WINEDEBUG="${WINEDEBUG:--all}"
    cd -- "$(dirname -- "$exe")"
    exec "$PROTONPATH/files/bin/wine64" "$exe" "$@"
  fi
else
  # Match UMU's large descriptor budget for the shared server.
  ulimit -n "$(ulimit -Hn)"
  WINEPREFIX="$state/prefix/pfx" WINEFSYNC="$fsync" WINEESYNC="$esync" "$server" -p 9>&- || { status=$?; [[ "$status" == 2 ]] || exit "$status"; }
fi
if [[ "${SM4L_UI_COMPAT:-0}" == 1 ]]; then
  nohup python3 -B "$sm4l_root/addin/spacemouse.py" --ui-only >"$log_dir/ui-compat.log" 2>&1 </dev/null 9>&- &
fi
# The CAD shortcut enables navigation after the host server is safely running.
if [[ "${SM4L_SPACEMOUSE:-0}" == 1 ]]; then
  nohup python3 -B "$sm4l_root/addin/spacemouse.py" >"$log_dir/spacemouse.log" 2>&1 </dev/null 9>&- &
fi
export PROTON_LOG=1 PROTON_LOG_DIR="$log_dir"
cd -- "$(dirname -- "$exe")"
if (( oneshot )); then
  # Not exec: when this was the run that created the prefix, make the profile folders afterwards, then pass the exit code on.
  status=0
  "${UMU_RUN:-umu-run}" "$exe" "$@" || status=$?
  ensure_profile_folders
  exit "$status"
fi
exec "${UMU_RUN:-umu-run}" "$exe" "$@"
