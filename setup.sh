#!/usr/bin/env bash
# Walk the SM4L install in order. Each step checks the current state first, so a rerun skips what is
# already done. Manual steps (vendor downloads and GUI installers) stop and wait for you. Steps that
# reach the network or run winetricks ask before they start.
#
#   setup.sh --plan    print each step and whether it is done, todo or manual. Changes nothing.
#   setup.sh           run the steps that aren't done yet.
#
# The step order and the reasons behind it are in docs/INSTALL.md.
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export SM4L_ROOT="$root"
export SOLIDWORKS_PROTON_STATE="${SOLIDWORKS_PROTON_STATE:-$HOME/.local/share/solidworks-proton}"
export PROTONPATH="${PROTONPATH:-$HOME/.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4}"
export UMU_RUN="${UMU_RUN:-$HOME/.local/bin/umu-run}"
export PROTON_NO_FSYNC=1 PROTON_NO_ESYNC=1 PROTON_USE_XALIA=0 PROTON_VERB=run WINEDEBUG=-all
export WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix" GAMEID=umu-default
PFX="$SOLIDWORKS_PROTON_STATE/prefix/pfx"
LAUNCH="$root/bin/launch_proton.sh"
PLAN=0
[[ "${1:-}" == "--plan" ]] && PLAN=1

pwine() {
  env WINEPREFIX="$PFX" WINEFSYNC=0 WINEESYNC=0 WINEDEBUG=-all "$PROTONPATH/files/bin/wine64" "$@"
}
stop_prefix() {
  WINEPREFIX="$PFX" "$PROTONPATH/files/bin/wineserver" -k 2>/dev/null || true
}
ask() {  # ask "question": returns 0 on yes. Non-interactive runs say no.
  [[ -t 0 ]] || return 1
  read -r -p "$1 [y/N] " reply
  [[ "$reply" == [yY]* ]]
}
pause() {
  [[ -t 0 ]] && read -r -p "$1 Press Enter when it's done, or Ctrl-C to stop. " _ || true
}
# reg_value FILE KEY VALUE: read the value from the prefix's user.reg or system.reg, offline, without starting Wine.
# Prints nothing when the key or value is missing. Wine writes these files when its server exits.
reg_value() {
  python3 -B "$root/setup/reg_query.py" "$PFX/$1" "$2" "$3" 2>/dev/null || true
}

# Each step: a check (exit 0 when done), a label, and an action. Steps run in the order listed.
declare -a STEPS=()
step() { STEPS+=("$1|$2|$3|$4"); }  # id|kind|label|check-function

check_tools() {
  local t
  for t in python3 curl 7z clang lld-link; do command -v "$t" >/dev/null || return 1; done
  [[ -f /usr/lib/wine/x86_64-windows/libkernel32.a ]]
}
check_umu() { [[ -x "$UMU_RUN" && -d "$PROTONPATH/files/bin" ]]; }
check_prefix() { [[ -d "$PFX/drive_c" ]]; }
check_dotnet() { [[ -f "$PFX/drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/RegAsm.exe" ]]; }
# Done only when setup.exe has the pinned hash and every file of the vendor manifest is there with the right total size
# (so a copy that is still running does not count). Once the platform is installed the media may have been trimmed.
check_media() {
  local extra=()
  if check_platform; then extra=(--allow-pruned); fi
  python3 -B "$root/setup/media_check.py" "${MEDIA_1:-/nonexistent}" media "${extra[@]}" >/dev/null 2>&1
}
# Done only when the patched copy is exactly what setup/patch_offline_installer.py makes from the original setup.exe.
check_offline_patch() { python3 -B "$root/setup/media_check.py" "${MEDIA_1:-/nonexistent}" patch >/dev/null 2>&1; }
check_platform() { [[ -f "${PLATFORM_BIN:-/nonexistent}/CATSysTS.dll" ]]; }
# Done when the platform's CATSysTS.dll imports the proxy, or when its backup is there.
check_dir_compat() {
  local dll="${PLATFORM_BIN:-/nonexistent}/CATSysTS.dll"
  [[ -f "$dll.pre-swcompat" ]] || grep -q -a -F 'swcompat.dll' "$dll" 2>/dev/null
}
check_cad() { [[ -f "${CAD_DIR:-/nonexistent}/sldworks.exe" ]]; }
check_webview() { [[ -n "$(find "$PFX/drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application" -name msedgewebview2.exe 2>/dev/null | head -1)" ]]; }
check_browser_profile() { [[ -f "$SOLIDWORKS_PROTON_STATE/browser-windows-firefox/user.js" ]]; }
check_browser_reg() { [[ "$(reg_value user.reg 'Software\Wine\WineBrowser' Browsers)" == "$root/bin/open_windows_firefox.sh" ]]; }
# The service is stored under ControlSet001 in system.reg, and sometimes under CurrentControlSet.
check_launcher_type() {
  [[ "$(reg_value system.reg 'System\ControlSet001\Services\3DEXPERIENCELauncher' Type)" == "0x110" ]] ||
  [[ "$(reg_value system.reg 'System\CurrentControlSet\Services\3DEXPERIENCELauncher' Type)" == "0x110" ]]
}
check_units() {
  local u
  for u in sm4l-launcher sm4l-spacemouse sm4l-ui-compat; do
    [[ -f "$HOME/.config/systemd/user/$u.service" ]] || return 1
    grep -q "$root" "$HOME/.config/systemd/user/$u.service" || return 1
  done
}
check_header_guard() { [[ -n "${HEADER_DLL:-}" && -f "$(dirname -- "$HEADER_DLL")/comctl32.before-header-guard.dll" ]]; }
check_theme_off() { [[ "$(reg_value user.reg 'Software\Microsoft\Windows\CurrentVersion\ThemeManager' ThemeActive)" == "0" ]]; }
check_msxml6() { python3 -B "$root/setup/install_msxml6.py" --check >/dev/null 2>&1; }
check_menu() { [[ -f "$HOME/.local/share/applications/SM4L-solidworks.desktop" ]] && grep -q "$root/bin/launch_solidworks.sh" "$HOME/.local/share/applications/SM4L-solidworks.desktop"; }

act_tools() { echo "Install the host tools listed in docs/INSTALL.md, step 2, then run this again."; return 1; }
act_umu() { echo "Install umu-run and UMU-Proton-10.0-4, as in docs/INSTALL.md, step 4."; return 1; }
act_prefix() { "$LAUNCH" "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0; }
act_dotnet() {
  ask "Install .NET 4.8 with winetricks? It downloads from the network." || { echo "Skipped."; return 1; }
  "$UMU_RUN" winetricks -q dotnet48
  stop_prefix
}
act_media() {
  echo "Get the vendor ZIP (docs/DOWNLOAD.md), extract it, then set MEDIA_1 to the folder with setup.exe."
  pause "Waiting for the vendor media."
  check_media || python3 -B "$root/setup/media_check.py" "${MEDIA_1:-/nonexistent}" media >&2 || true
  check_media
}
act_offline_patch() {
  python3 -B "$root/tests/test_patch_offline_installer.py" "$MEDIA_1"
  python3 -B "$root/setup/patch_offline_installer.py" "$MEDIA_1/setup.exe"
}
act_platform() {
  echo "Run the platform installer. It stops at the dictionary compile, which is expected."
  "$LAUNCH" "$MEDIA_1/setup_admin_proton_offline.exe"
  pause "When the first install stops."
}
act_dir_compat() {
  python3 -B "$root/tests/test_directory_compat.py" "$PLATFORM_BIN/CATSysTS.dll"
  python3 -B "$root/setup/apply_directory_compat.py" "$PLATFORM_BIN/CATSysTS.dll"
  echo "Before you click Restart installation, run this in a second terminal:"
  echo "  python3 -B $root/setup/apply_directory_compat.py \"$PLATFORM_BIN/CATSysTS.dll\" --watch-for-recopy"
  pause "Re-run the platform installer and let it finish."
}
act_cad() {
  echo "Install SOLIDWORKS Design 2026 SP3.0 through Installation Manager, or with the helper in docs/INSTALL.md, step 8."
  pause "When the CAD install finishes."
}
act_webview() {
  echo "Install WebView2 from docs/INSTALL.md, step 9."
  pause "When WebView2 is installed."
}
act_browser_profile() {
  echo "Set SOLIDWORKS_PLATFORM_URL and sign in to the Windows-identifying profile (docs/INSTALL.md, step 10)."
  pause "When the login profile works."
}
act_browser_reg() {
  python3 -B "$root/bin/register_paths.py"
}
act_launcher_type() {
  stop_prefix
  pwine reg.exe add 'HKLM\System\CurrentControlSet\Services\3DEXPERIENCELauncher' /v Type /t REG_DWORD /d 0x110 /f
  stop_prefix
}
act_units() { "$root/bin/install_units.sh"; systemctl --user daemon-reload; }
act_header_guard() {
  python3 -B "$root/tests/test_patch_header_layout.py" "$HEADER_DLL"
  python3 "$root/setup/patch_header_layout.py" "$HEADER_DLL"
  pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v comctl32 /t REG_SZ /d native,builtin /f
}
act_theme_off() {
  stop_prefix
  cp "$PFX/user.reg" "$SOLIDWORKS_PROTON_STATE/user.reg.before-theme-off"
  pwine reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\ThemeManager' /v ThemeActive /t REG_SZ /d 0 /f
  stop_prefix
}
act_msxml6() {
  ask "Install native msxml6 for CAD? This needs the cached KB2957482 package and 7z." || { echo "Skipped."; return 1; }
  stop_prefix
  python3 -B "$root/setup/install_msxml6.py"
  stop_prefix
}
act_menu() { python3 -B "$root/bin/install_desktop.py"; }

step preflight-tools auto "Host tools (python3, curl, 7z, clang, lld, Wine import libraries)" check_tools
step umu auto "umu-run and UMU-Proton-10.0-4" check_umu
step prefix auto "Initialise the Wine prefix" check_prefix
step dotnet network ".NET 4.8 through winetricks (network)" check_dotnet
step media manual "Vendor media extracted (MEDIA_1 set)" check_media
step offline-patch auto "Offline installer patched" check_offline_patch
step platform manual "Platform installed (first run stops at the dictionary compile)" check_platform
step dir-compat auto "Directory compat proxy applied to CATSysTS.dll" check_dir_compat
step cad manual "SOLIDWORKS Design CAD installed (sldworks.exe present)" check_cad
step webview manual "WebView2 runtime installed" check_webview
step browser-profile manual "Windows-identifying login profile signed in" check_browser_profile
step browser-reg auto "Wine browser handler points at this checkout" check_browser_reg
step launcher-type auto "Launcher service is interactive (Type 0x110)" check_launcher_type
step units auto "Background units installed for this checkout" check_units
step header-guard auto "Header guard applied to comctl32 in the prefix" check_header_guard
step theme-off auto "Theme off so checkbox and radio labels draw" check_theme_off
step msxml6 network "Native msxml6 for CAD (verified once)" check_msxml6
step menu auto "Menu entry points at this checkout" check_menu

action_for() {
  case "$1" in
    preflight-tools) echo act_tools ;;
    umu) echo act_umu ;;
    prefix) echo act_prefix ;;
    dotnet) echo act_dotnet ;;
    media) echo act_media ;;
    offline-patch) echo act_offline_patch ;;
    platform) echo act_platform ;;
    dir-compat) echo act_dir_compat ;;
    cad) echo act_cad ;;
    webview) echo act_webview ;;
    browser-profile) echo act_browser_profile ;;
    browser-reg) echo act_browser_reg ;;
    launcher-type) echo act_launcher_type ;;
    units) echo act_units ;;
    header-guard) echo act_header_guard ;;
    theme-off) echo act_theme_off ;;
    msxml6) echo act_msxml6 ;;
    menu) echo act_menu ;;
  esac
}

# Steps that need the path of the vendor files or the prefix's DLLs. Set them from the environment,
# or the steps that need them report a clear message instead of guessing.
export MEDIA_1="${MEDIA_1:-$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1}"
export PLATFORM_BIN="${PLATFORM_BIN:-$PFX/drive_c/Program Files/Dassault Systemes/SOLIDWORKS 3DEXPERIENCE R2026x/win_b64/code/bin}"
export CAD_DIR="${CAD_DIR:-$PFX/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS}"
export HEADER_DLL="${HEADER_DLL:-$PFX/drive_c/windows/winsxs/amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.0.2600.2982_none_deadbeef/comctl32.dll}"

pending=0
for entry in "${STEPS[@]}"; do
  IFS='|' read -r id kind label check <<<"$entry"
  if $check 2>/dev/null; then
    status=done
  elif [[ "$kind" == manual ]]; then
    status=manual
  else
    status=todo
  fi
  if (( PLAN )); then
    printf '%-8s %-14s %s\n' "$status" "$id" "$label"
    continue
  fi
  if [[ "$status" == done ]]; then
    printf 'done   %s\n' "$label"
    continue
  fi
  pending=1
  printf '\n== %s (%s)\n' "$label" "$kind"
  action="$(action_for "$id")"
  if ! $action; then
    echo "Stopped at: $label. Fix it, then run setup.sh again. Finished steps are skipped."
    exit 1
  fi
  if $check 2>/dev/null; then
    printf 'done   %s\n' "$label"
  else
    echo "Step not confirmed: $label. Check the output above, then run setup.sh again."
    exit 1
  fi
done

if (( ! PLAN )) && (( ! pending )); then
  echo "Everything in the plan is done. Launch CAD from the menu entry, then check docs/INSTALL.md, step 18."
fi
