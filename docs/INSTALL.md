# Install SOLIDWORKS on Arch Linux

This is the full path, in order. It's based on one working Arch Linux x86_64 laptop with an Intel GPU, set up in October 2026. Nobody has replayed it on a fresh machine yet, so check each step's result before you move on.

`setup.sh` in the repository root runs the scriptable steps in this order. `./setup.sh --plan` shows where you are and changes nothing. The media step checks the vendor files before the installer runs, and the offline-patch step checks the patched copy byte for byte. It's pending a live test, so this guide is the reference.

Every step ends with a check. If the check fails, stop and read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) before going further.

Each step carries a status:

- **Verified:** worked on the reference machine as written.
- **Verified once:** worked in one run. Expect to re-check it.
- **Pending:** written or built, but not yet confirmed in a real CAD run. It's optional until it is.

## What you need

- An Arch Linux x86_64 install on KDE Plasma under Wayland, which means KWin. The reference machine runs that setup.
- A SOLIDWORKS Makers or 3DEXPERIENCE SOLIDWORKS account, with a license assigned to you. SM4L doesn't provide one.
- Plenty of free disk space. The full ZIP alone is about 28 GB, and the extracted media, the installed CAD, the prerequisites and temp files take more.
- A Firefox install for the Windows-identifying login profile.
- A SpaceMouse is optional. See [SPACEMOUSE.md](SPACEMOUSE.md).

SM4L doesn't include any vendor binaries, media, licenses or installed prefixes. You get all of those from the vendor and Microsoft, under your own account.

## 1. Get the vendor media

**Status: verified.** Follow [DOWNLOAD.md](DOWNLOAD.md). It covers the Windows-identifying Firefox profile, the download path through the vendor site, and how to check the ZIP.

When you finish, you should have:

- `SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip`, or the release Dassault offers you, with its filename written down. The patches here are pinned to the reference release and refuse anything else.
- The SOLIDWORKS Design 2026 SP3.0 installation, downloaded later through Installation Manager in step 7.

## 2. Install the host tools

**Status: verified.**

```bash
sudo pacman -S --needed git python firefox clang lld wine unzip cabextract curl p7zip
```

The host `wine` package only provides import libraries for the builds below. The app runs under the pinned Proton Wine, not `/usr/bin/wine`. Check the libraries exist:

```bash
ls /usr/lib/wine/x86_64-windows/lib{kernel32,ntdll,user32,comctl32,msi}.a
```

## 3. Clone the repository and set the environment

**Status: verified.**

```bash
git clone https://github.com/nomadsgalaxy/SM4L.git
cd SM4L
export SM4L_ROOT="$PWD"
export SOLIDWORKS_PROTON_STATE="$HOME/.local/share/solidworks-proton"
export PROTONPATH="$HOME/.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4"
export UMU_RUN="$HOME/.local/bin/umu-run"
export LAUNCH="$SM4L_ROOT/bin/launch_proton.sh"
export PROTON_NO_FSYNC=1 PROTON_NO_ESYNC=1 PROTON_USE_XALIA=0
export PROTON_VERB=run WINEDEBUG=-all
export WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix" GAMEID=umu-default
mkdir -p "$SOLIDWORKS_PROTON_STATE"
chmod +x bin/*.sh
"$LAUNCH" --check
```

Run every command in this guide from one terminal that has these variables set. Keep your current session's `DISPLAY`, `XAUTHORITY` and `WAYLAND_DISPLAY`. Don't copy another machine's `XAUTHORITY` file name into this setup.

**Check:** `"$LAUNCH" --check` exits 0.

## 4. Install UMU and Proton

**Status: verified.**

Download `umu-launcher-1.4.4-zipapp.tar` from the [official 1.4.4 release](https://github.com/Open-Wine-Components/umu-launcher/releases/tag/1.4.4). Extract `umu-run` into `~/.local/bin`, and make it executable. The reference copy has this SHA256:

```text
d0005a58602041229cc467dab03dc0c0b9e8cce09a8145b16b7683244cf17804
```

Install [UMU-Proton-10.0-4](https://github.com/Open-Wine-Components/umu-proton/releases/tag/UMU-Proton-10.0-4) under `~/.local/share/Steam/compatibilitytools.d/`. UMU can download and verify it for you. The DLL patches here are pinned to this release, so a newer Proton is a separate experiment.

**Check:** `ls "$PROTONPATH/files/bin/wine64"` lists the binary.

## 5. Initialise the prefix

**Status: verified.**

Create the prefix with a short one-shot command. `--oneshot` runs no persistent server. It returns when the program exits, with that program's exit code:

```bash
"$LAUNCH" --oneshot "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0
```

Normal mode starts the persistent server and is for CAD and the vendor launchers. `--oneshot` is for short setup commands: it returns when the program exits, with that program's exit code, and it refuses to start CAD or its launcher. The launcher also initialises a missing or broken prefix itself before it starts the host server, so a fresh install doesn't need a separate step. Starting the server before that overwrote Proton's default registry with a tiny one, and installers such as dotnet40 then failed with status 5. `--oneshot` also refuses to start CAD or its launcher.

Define the registry helper once the prefix exists. It runs registry commands in the prefix without the fsync and esync settings that the launcher uses:

```bash
pwine() {
  env WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" \
    WINEFSYNC=0 WINEESYNC=0 WINEDEBUG=-all \
    "$PROTONPATH/files/bin/wine64" "$@"
}
```

**Check:** `ls "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c"` lists `windows` and `Program Files`, and `system.reg` has a `[Software\\Classes\\CLSID]` section. A healthy prefix's `system.reg` is a few megabytes. A prefix of about 250 KB is broken, and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) explains the fix.

`launch_proton.sh` starts the persistent Wine server on the host before UMU builds its container. It keeps fsync and esync off, and it raises the file-descriptor limit. Every launch into this prefix has to use the same Proton and sync settings.

If you ever need to stop the prefix's server, close CAD first, then run:

```bash
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Don't stop another prefix, or a session with unsaved work.

## 6. Install .NET 4.8 and set Windows 11 for the installer

**Status: verified.** This step downloads from the network, so it asks you to confirm first.

```bash
"$UMU_RUN" winetricks -q dotnet48
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
"$LAUNCH" --oneshot "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32/winecfg.exe" -v win11
pwine 'C:\windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe' /?
```

The `winecfg` call runs and exits 0 on a fresh prefix. On a scratch prefix it didn't leave a `win11` value in `user.reg`, because the Proton default may already be the target version, so this step shows only that the command returns. The `reg.exe` and `RegAsm` lines keep `pwine`, which returns on its own. Each `pwine` call starts a Wine server when none is running, and that server writes `user.reg` when it exits, so keep the `wineserver -k` line after the registry blocks.

The media's own .NET 4.8.1 installer reported success without installing the 64-bit RegAsm, and the Login Manager registration still failed. Winetricks' .NET 4.8 recipe fixed it.

**Check:** `RegAsm.exe /?` prints its usage, and does not report a missing file.

## 7. Install the platform

**Status: verified.**

Extract the vendor ZIP into the state directory, then point `MEDIA_1` at the folder that holds `setup.exe`, `setup_noUAC.exe` and `media.db`:

```bash
export MEDIA_1="$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1"
python3 -B "$SM4L_ROOT/tests/test_patch_offline_installer.py" "$MEDIA_1"
python3 -B "$SM4L_ROOT/setup/patch_offline_installer.py" "$MEDIA_1/setup.exe"
"$LAUNCH" "$MEDIA_1/setup_admin_proton_offline.exe"
```

Check the media before you patch anything:

```bash
python3 -B "$SM4L_ROOT/setup/media_check.py" "$MEDIA_1"
```

This checks `setup.exe`'s pinned SHA256, and that every file in the vendor manifest `0data/MediaContent.xml` exists in folders `1` to `7` under `MEDIA_1`'s parent. The supported release has 575 files, totalling 28,567,415,757 bytes. Until the platform is installed, all seven folders must be present. After the install, trimmed media is accepted, and only `setup.exe`'s hash is checked. For a full SHA256 pass over every file, which is slower, add `hashes`: `python3 -B "$SM4L_ROOT/setup/media_check.py" "$MEDIA_1" hashes`.

The patch checks the whole file's hash first, then changes only the IE10 export check, in a separately named copy. It skips a false prerequisite check for the missing `HttpWebSocketReceive`. It doesn't implement WebSockets. The original media isn't touched, and the patched copy's signature is no longer valid.

Use the administrator entry point, `setup_admin_proton_offline.exe`. `setup_noUAC.exe` ran into a vendor elevation error on the reference machine.

On the reference machine I selected W4Y (3DEXPERIENCE SOLIDWORKS Ultimate), default install directory, updates on demand. The same prefix later launched Professional for Makers with the account's license. Choose the edition your license covers. The guide doesn't claim a route to a different tier.

**Check:** the installer finishes, and the platform directory exists:

```bash
export PLATFORM_BIN="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS 3DEXPERIENCE R2026x/win_b64/code/bin"
ls "$PLATFORM_BIN/CATSysTS.dll"
```

The first install fails at the Object Modeler dictionary compile, because the installed `CATSysTS.dll` looks up `RtlIsNameInExpression`, and Wine doesn't export it. Apply the wildcard matcher after that first run stops:

```bash
python3 -B "$SM4L_ROOT/tests/test_directory_compat.py" "$PLATFORM_BIN/CATSysTS.dll"
python3 -B "$SM4L_ROOT/setup/apply_directory_compat.py" "$PLATFORM_BIN/CATSysTS.dll"
```

This uses the checked-in `setup/swcompat.dll`, saves `CATSysTS.dll.pre-swcompat`, and rewrites only the KERNEL32 import provider. The proxy forwards everything that already exists, and it adds Unicode and DOS wildcard matching when NTDLL doesn't have it.

The installer's **Restart installation** copies the original DLL back. Before you click it, run the watcher in a second terminal with the same environment:

```bash
python3 -B "$SM4L_ROOT/setup/apply_directory_compat.py" "$PLATFORM_BIN/CATSysTS.dll" --watch-for-recopy
```

The watcher waits up to 15 minutes for the exact original bytes to reappear, then patches them again. On the reference machine the dictionary compiler then returned zero, wrote a 190,218-byte dictionary, and the platform install finished.

To roll back this step, restore the original `CATSysTS.dll` from `CATSysTS.dll.pre-swcompat` in the platform `bin` folder, and delete the `swcompat.dll` beside it. Older installs may have the original at `$SOLIDWORKS_PROTON_STATE/directory-compat/CATSysTS.original.dll` instead, from the first manual flow before the apply script existed. Check both places before you change anything.

If you'd rather rebuild the proxy than use the checked-in one, run `setup/build_directory_compat.py` on the `.pre-swcompat` file with an output directory that doesn't exist yet, then pass `--shim` to the apply script. Every guarded patch refuses builds it doesn't know.

## 8. Install SOLIDWORKS Design CAD

**Status: verified.**

Use the vendor Installation Manager to download **SOLIDWORKS Design 2026 SP3.0** and its prerequisites. Keep the `PreReqs`, `Toolbox` and `swwi` download folders. On the reference machine the manager downloaded and ran the prerequisites, then the CAD MSI's ZIP step failed.

```bash
export CAD_DATA="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/users/steamuser/Downloads/3DEXPERIENCE SOLIDWORKS Downloads/2026 SP3.0/swwi/data"
export CAD_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS"
```

`InstallSpatialIOP` failed on the reference machine, because the Windows ZIP-shell API returned `0x8000ffff`. The fix is to extract the real `spatialiop.zip` yourself, check every entry's CRC and size, and turn off only that extraction step in a separate copy of the MSI:

```bash
python3 -B "$SM4L_ROOT/tests/test_prepare_design_install.py"
python3 "$SM4L_ROOT/setup/prepare_design_install.py" "$CAD_DATA" "$CAD_DIR"
clang --target=x86_64-pc-windows-msvc -O2 -Wall -Wextra -Werror -fno-builtin \
  -c "$SM4L_ROOT/experiments/cad-msi-experiment.c" -o "$SOLIDWORKS_PROTON_STATE/cad-msi.obj"
lld-link /entry:entry /subsystem:console /nodefaultlib /machine:x64 \
  "/out:$SOLIDWORKS_PROTON_STATE/cad-msi.exe" "$SOLIDWORKS_PROTON_STATE/cad-msi.obj" \
  /usr/lib/wine/x86_64-windows/libkernel32.a /usr/lib/wine/x86_64-windows/libmsi.a
"$LAUNCH" "$SOLIDWORKS_PROTON_STATE/cad-msi.exe"
```

The C helper runs the install with the Windows cache and install paths above hard-coded. It checks the custom action's target, sets `InstallSpatialIOP`'s condition to `0`, and calls `MsiInstallProductW`. Use it only with the release it was written for, and only after the real ZIP has been extracted.

The optional-feature list from Installation Manager returned success without installing the CAD core. `ADDLOCAL=ALL` installed the real `sldworks.exe`. Check the MSI's result and the executable, not whether a UMU supervisor process is still running.

**Check:**

```bash
ls "$CAD_DIR/sldworks.exe"
```

## 9. Install WebView2

**Status: verified.** Download Microsoft's x64 Evergreen standalone installer from its [official link](https://go.microsoft.com/fwlink/p/?LinkId=2124701). On the reference machine the installer's hash was `ac22ecdc19c5b88b87f3fa752c00da9541653a8f5c0c5fc4a3b2b6ebe6591f69`, and it installed runtime `154.0.4258.62`. The link changes over time, so a newer runtime is something to note, not a mismatch.

```bash
"$LAUNCH" "$SOLIDWORKS_PROTON_STATE/MicrosoftEdgeWebView2RuntimeInstallerX64.exe" /silent /install
```


The installer spawns its own children, so judge success by the result: `msedgewebview2.exe` is present (the check below), not by when the launcher returns.
**Check:** `msedgewebview2.exe` exists under `drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/<version>/`, and the EdgeUpdate registration shows `pv` and `LastInstallerError=0`.

Keep Proton's `msedgewebview2.exe` `Version=win7` override. The reference machine tried `win11` first, and the startup failures came back until `win7` was restored. That's what worked there. It isn't a Microsoft statement about Windows 7 support.

Use Wine's builtin D3D libraries for the embedded runtime only:

```bash
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v dxgi /t REG_SZ /d builtin /f
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v d3d11 /t REG_SZ /d builtin /f
```

The login page only rendered after the two vendor executables got HKLM policy arguments. Elevated WebView startup ignored environment and HKCU arguments:

```bash
export WEBVIEW_FLAGS='--enable-logging --v=1 --log-file=C:\webview-blank.log --use-gl=angle --use-angle=swiftshader'
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v ENOPLMCSAClient.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v SWXDesktopLauncher.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
```

That log can contain sign-in URLs and tickets, so keep it local. This setup doesn't use `--no-sandbox` or any web-security bypass. SwiftShader only renders the embedded login. It's separate from CAD's OpenGL setting.

## 10. Set up the Windows-identifying login profile

**Status: verified.** Set your own HTTPS platform URL. The repository doesn't include anyone's tenant or dashboard IDs:

```bash
export SOLIDWORKS_PLATFORM_URL='https://YOUR-PLATFORM-HOST.3dexperience.3ds.com/'
python3 -B "$SM4L_ROOT/bin/launch_windows_browser.py"
```

The helper sets up a dedicated `browser-windows-firefox` profile. It checks the profile's real HTTP User-Agent and JavaScript navigator fields against a local page, then opens the platform. Sign in yourself. The helper stays running while Firefox is open. Close that browser before you rerun the profile setup, and leave your other Firefox profiles alone.

Send only this prefix's login links to the dedicated profile. This registers the handler and refreshes the menu entry for this checkout:

```bash
python3 -B "$SM4L_ROOT/bin/register_paths.py"
```

With a wineserver running for the prefix, the script uses the prefix's `wine64 reg add`. Otherwise it edits `user.reg` offline, and it never starts a mismatched wineserver. `--check` shows what it would do without changing anything.

The handler opens Firefox outside the container, through UMU's `steam-runtime-launch-client --host --`. It only handles links from inside UMU. Your normal browser defaults don't change.

**Important:** this registry value stores the checkout's absolute path. If you move the checkout, or pull the reorganized layout, run `bin/register_paths.py` again. The migration note covers this.

## 11. Start the vendor launcher service

**Status: verified.** The website looks for the installed `3DEXPERIENCELauncher` service. A connected browser isn't enough. With the desktop environment available:

```bash
pwine sc.exe query 3DEXPERIENCELauncher
pwine sc.exe start 3DEXPERIENCELauncher
curl --head --max-time 5 http://127.0.0.1:20250/
```

The reference machine returned HTTP 200. If the service is already running, a second start can be rejected, so query it first and check the endpoint before assuming it failed.

Mark the service interactive. This is the change that made platform-launched CAD appear on screen:

```bash
pwine reg.exe add 'HKLM\System\CurrentControlSet\Services\3DEXPERIENCELauncher' /v Type /t REG_DWORD /d 0x110 /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Wine starts every service on a hidden desktop (`__wineservice_winstation\Default`) unless it has the `SERVICE_INTERACTIVE_PROCESS` flag (`0x100`). The vendor service was `0x10`, so the launcher backbone and every CAD copy it started ran with no display. `0x110` keeps the service's own-process type and adds the interactive flag. Close CAD before you stop the prefix, because the flag applies when the service starts again.

If the website stalls, start the tray by hand, then click **Open** once and accept the vendor's trusted-platform prompt:

```bash
export LAUNCHER_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/3DEXPERIENCE Launcher"
"$LAUNCH" "$LAUNCHER_DIR/3DEXPERIENCELauncherSysTray.exe"
```

Starting `sldworks.exe` directly doesn't skip the platform. CAD hands off to `SWXDesktopLauncher`, which asks you to open 3DEXPERIENCE in the browser and click **Open**. The service then starts CAD again. That second copy is the one you use.

If you see HTTP 403 or license error 1002, check your account, tenant and assigned role. Don't assume a purchased role is assigned, and don't patch a license result.

## 12. Install the background units

**Status: pending.** This is new in the reorganized layout. The units in `units/` are templates. The installer fills in your checkout path, so you don't edit the unit files by hand.

```bash
"$SM4L_ROOT/bin/install_units.sh"
systemctl --user enable --now sm4l-launcher.service
```

`install_units.sh` renders the templates with this checkout's path, writes them to `~/.config/systemd/user`, removes stale `sm4l-*` units, and reloads systemd. It doesn't restart a running unit. Pass `--restart` only with CAD closed.

- `sm4l-launcher.service` boots the prefix's launcher tray at login, so `127.0.0.1:20250` answers before you click Open. After a KWin restart, restart it, because `XAUTHORITY` changes.
- `sm4l-spacemouse.service` attaches the SpaceMouse add-in to each new `sldworks.exe`. Enable it after the driver is set up in [SPACEMOUSE.md](SPACEMOUSE.md).
- `sm4l-ui-compat.service` carries the header fix and off-screen dialog recovery. Enable it.

Exit code 2 means another bridge already holds the prefix lock. The units don't restart on that code.

**Check:** `systemctl --user status sm4l-launcher.service` shows the unit running, and `curl --head --max-time 5 http://127.0.0.1:20250/` answers.

### A note on the 3DEXPERIENCE PLM connector hook

The UI add-in unhooks the 3DEXPERIENCE PLM connector's `WH_CALLWNDPROC` hook after startup, because that hook adds a large share of the UI-thread cost under Wine. This is on by default, and the build loads at the next CAD start. On the reference machine, the in-CAD batch rebuild median went from 135 ms (range 88 to 403 ms) to 52 ms (range 46 to 63 ms), measured on 2026-10-08. A local-files workflow was checked by hand.

It has a cost. The connector also tracks windows for 3DEXPERIENCE features, including saving and opening from the platform, the 3DEXPERIENCE tab or task pane, lifecycle and collaboration. Unhooking it disables that tracking. Local files work normally, and that's the workflow that's been checked. Nothing has been tested for the 3DEXPERIENCE platform workflows. If you use them, create the file `C:\sm4l-unhook-pdm-off` in the prefix's `drive_c` folder, then restart CAD to keep the hook. A CAD restart brings the hook back, and the add-in never changes the DLL on disk.

## 13. Apply the header-control crash fix

**Status: verified.** Patch the prefix's amd64 copy of Wine's Common Controls before opening CAD:

```bash
export HEADER_DLL="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/winsxs/amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.0.2600.2982_none_deadbeef/comctl32.dll"
python3 -B "$SM4L_ROOT/tests/test_patch_header_layout.py" "$HEADER_DLL"
python3 "$SM4L_ROOT/setup/patch_header_layout.py" "$HEADER_DLL"
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v comctl32 /t REG_SZ /d native,builtin /f
```

The supported Wine DLL hash is `d0616fbdb1649047ac7f0fea3a55f8ab70b33b4c0703c056a6706c43c0cf1676`. The patch saves `comctl32.before-header-guard.dll` beside the original. It catches a null `HDM_LAYOUT` pointer and returns FALSE. Valid layouts still run the original code. The override applies only to `sldworks.exe`.

A prefix refresh can copy the original back. If startup crashes again, compare the current DLL with the backup. Running the patch on an already patched file is refused on purpose.

## 14. Turn off the theme so checkbox and radio labels draw

**Status: verified** on the reference machine on 2026-10-08. Under the prefix's Windows theme, SOLIDWORKS' PropertyManager checkboxes and radio buttons draw without their labels. Turning the theme off makes SOLIDWORKS use classic controls. The look is flatter, and the labels render.

Close CAD and stop the prefix's server first. Back up the registry, then set the value:

```bash
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/user.reg" "$SOLIDWORKS_PROTON_STATE/user.reg.before-theme-off"
pwine reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\ThemeManager' /v ThemeActive /t REG_SZ /d 0 /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

`pwine` starts its own server, which writes `user.reg` when it exits. The `wineserver -k` line makes sure that write happens before the next launch.

`launch_proton.sh` calls `setup/ensure_theme_off.py` before every start, so it re-applies `ThemeActive=0` automatically, including after a prefix update. Its tests pass, but it hasn't been confirmed in a real start yet. Until it is, re-running this step after a prefix update is the fallback.

To roll back, close CAD, stop the prefix, and restore the backup. That restores the whole `user.reg`, so it also undoes any other registry changes made since the backup. To only switch the theme back on, set `ThemeActive` to `1`. The original value was `1`, with `DllName` pointing at `light.msstyles`.

## 15. Install native msxml6 so 3MF Save As works

**Status: verified once** on 2026-10-08. Save As 3MF completed, CAD started cleanly with no popups, and the file imported into PrusaSlicer. Keep this in the list until it passes on a retry.

Without this, Save As 3MF crashes CAD. The builtin msxml3 that Wine ships miscounts document references when nodes move between documents, so a later read reaches freed memory. Forcing native msxml6 for `sldworks.exe` avoids that path.

The scripted path does the whole step, and it checks hashes before copying. Stop the prefix's server first, and make sure you have the cached package (see below):

```bash
python3 -B "$SM4L_ROOT/setup/install_msxml6.py" --check
python3 -B "$SM4L_ROOT/setup/install_msxml6.py"
```

It needs `7z`, and the KB2957482 package cached by winetricks as `msxml6-KB2957482-enu-amd64.exe`. The package comes from [Microsoft's download page](https://download.microsoft.com/download/2/7/7/277681BE-4048-4A58-ABBA-259C465B1699/msxml6-KB2957482-enu-amd64.exe). Its SHA256 is `260cd870851ffc3c6d10b71691f134e20d8d03ac26073bb36951eacb7aa85897`.

The manual steps, if you want them, are the reference:

```bash
sha256sum msxml6-KB2957482-enu-amd64.exe
7z x -y msxml6-KB2957482-enu-amd64.exe
7z x -y msxml6.msi
```

The files inside are named by their MSI file key. The 64-bit and 32-bit builds differ by the key suffix. Copy each to the name CAD expects:

```bash
MSXML_SRC="$PWD"
SYS32="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32"
SYSWOW="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/syswow64"
cp "$MSXML_SRC/msxml6.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB" "$SYS32/msxml6.dll"
cp "$MSXML_SRC/msxml6r.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB" "$SYS32/msxml6r.dll"
cp "$MSXML_SRC/msxml6.dll.86F857F6_A743_463D_B2FE_98CB5F727E09" "$SYSWOW/msxml6.dll"
cp "$MSXML_SRC/msxml6r.dll.86F857F6_A743_463D_B2FE_98CB5F727E09" "$SYSWOW/msxml6r.dll"
```

Expected SHA256 values, before you copy:

- `system32` (x64): `msxml6.dll` `6fb5aead277001403cd01178346253455cdb9926b69f12ee99764ae358d7b21b`, `msxml6r.dll` `6e476a37fcff8ceab3ea9d08b381cc42238b00ad50b0fd05250b621c4ecdbce2`
- `syswow64` (x86): `msxml6.dll` `66fb552089d28797ed74afbff5ab2c739828cf9abb10579a6641d5bd51cdec7b`, `msxml6r.dll` `c4c3e734abbf54424f878457d93e4981f0ef19cfa974aeeacddfa916a508b185`

Before any of that, back up the registry and the msxml6 files:

```bash
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/user.reg" "$SOLIDWORKS_PROTON_STATE/user.reg.before-msxml6"
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/system.reg" "$SOLIDWORKS_PROTON_STATE/system.reg.before-msxml6"
mkdir -p "$SOLIDWORKS_PROTON_STATE/msxml6-backup"
cp "$SYS32/msxml6.dll" "$SOLIDWORKS_PROTON_STATE/msxml6-backup/system32-msxml6.dll"
cp "$SYSWOW/msxml6.dll" "$SOLIDWORKS_PROTON_STATE/msxml6-backup/syswow64-msxml6.dll"
```

Then set the override for CAD only, and stop the server:

```bash
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v msxml6 /t REG_SZ /d native,builtin /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

To roll back, close CAD and stop the prefix. Restore the two backed-up `msxml6.dll` files, delete both `msxml6r.dll` files, and remove the `msxml6` value under `AppDefaults\sldworks.exe\DllOverrides`. Restoring the `user.reg` and `system.reg` backups also works.

## 16. Launch CAD and set the graphics option

**Status: verified.**

```bash
"$LAUNCH" "$CAD_DIR/sldworks.exe"
```

The window identifies as **SOLIDWORKS Design Professional for Makers 2026 SP3.0 — For Personal Use Only**. On the reference machine, the menus and feature tree drew, but the part viewport and some panes were black.

Go to **Tools → Options → System Options → Performance**, clear **Enhanced graphics performance (requires SOLIDWORKS restart)**, apply, close CAD normally, and start it again. The setting saved on the reference machine was:

```text
HKCU\Software\SolidWorks\SOLIDWORKS 2026\Performance
Use Performance Pipeline 2020 = DWORD 0
```

Software OpenGL was greyed out before this change, and it stays off. The [vendor graphics guide](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P) covers the same troubleshooting.

**Check:** you can sketch, extrude and chamfer a cube, and the viewport renders.

## 17. Install the menu entry

**Status: verified.**

```bash
python3 -B "$SM4L_ROOT/bin/install_desktop.py"
desktop-file-validate "$HOME/.local/share/applications/SM4L-solidworks.desktop"
```

Search your app menu for **SOLIDWORKS for Makers**. The entry points at the checkout's absolute path, so rerun the installer if you move the checkout. It uses `$XDG_DATA_HOME/applications` when `XDG_DATA_HOME` is set. It's a user menu entry and needs no root.

## 18. Verify and record your checkpoint

Confirm the edition that's running, that sketch planes show up, and that you can sketch, extrude, chamfer, rotate, and exit normally. Save a test `.SLDPRT`, close CAD, reopen it, and check its features. Write down your GPU, package versions, and any differences from [tested-versions.json](tested-versions.json).

On the reference machine these have been confirmed: sketching, extruding, chamfering and rotating; SpaceMouse navigation; checkbox and radio labels with the theme off; the PropertyManager section headers through drag and resize; and Save As 3MF, verified once.

These are not confirmed yet: saving a `.SLDPRT` and reopening it, the default-on status-bar dedupe after a restart, the leftover-process cleanup on a real CAD exit, and the theme-off re-apply in a real start. Embedded browser panels still flash.

A splash screen or a running process doesn't count as a successful install.

## Checks

These run without launching CAD:

```bash
python3 -B tests/test_launch_proton.py
python3 -B tests/test_spacemouse.py
python3 -B tests/test_windows_browser.py
python3 -B tests/test_open_windows_firefox.py
python3 -B tests/test_prepare_design_install.py
python3 -B tests/test_directory_compat.py
python3 -B tests/test_cad_cleanup.py
python3 -B tests/test_swp_dedupe.py
python3 -B tests/test_install_units.py
python3 -B tests/test_reg_query.py
```

`tests/test_install_msxml6.py` runs against a throwaway prefix and needs `7z`. The probes under `experiments/` are reproductions, not checks.

## Where things are

| Path | What it holds |
| --- | --- |
| `bin/` | Scripts you run every day: launch, the launcher service, the menu entry, the browser profile, the unit installer |
| `setup/` | One-time install and patch steps, with the DLL proxy and its source |
| `addin/` | The SpaceMouse and UI add-in source, the bridge, the dedupe rules and the leftover-process cleanup |
| `units/` | systemd user unit templates. `bin/install_units.sh` fills in the checkout path |
| `tests/` | Assert-based checks for the scripts above |
| `experiments/` | Unverified or diagnostic tools and native probes. Don't run these as part of the install |
| `docs/` | This guide, the troubleshooting notes, the SpaceMouse guide, the download guide, the findings record and `tested-versions.json` |
