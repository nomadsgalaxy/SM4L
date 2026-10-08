# Replicate the reference machine setup on Arch Linux

This is the route that works on the reference machine: one Arch Linux laptop, tested in October 2026. It collects the working settings in one place. A fresh replay on a second machine hasn't been done yet, so check each step as you go. Some steps go through the vendor GUI.

Each section that needs a caveat says so at the top:

- **Verified:** worked on the reference machine as written.
- **Verified once:** worked in one run. Expect to re-check it.
- **Pending:** written or built, but not yet confirmed in a real CAD run. Treat it as optional until it is.

## 1. Match the versions and get your own downloads

What I pinned:

- Arch Linux x86_64. Reference renderer `Mesa Intel(R) Graphics (MTL)`.
- UMU 1.4.4 upstream zipapp, UMU-Proton-10.0-4, sniper runtime `3.0.20260928.262393`.
- Full platform media `SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip`.
- SOLIDWORKS Design 2026 SP3.0, MSI registered as `34.130.0150`.
- Microsoft .NET 4.8, installed through Proton's Winetricks recipe.
- Microsoft WebView2 x64 Evergreen runtime `154.0.4258.62`.

The exact reference package versions and supported file hashes are in [checkpoint.json](../checkpoint.json). Your GPU and package versions will probably be different. Write them down before changing anything.

If the site hides the download from Linux, start with [Download the installer from Linux](DOWNLOAD.md). It covers the Firefox identity setup, every menu step, and checking the media.

The full download lives under Compass → All Apps → Members Control Center → Configure Apps Installation → 3DEXPERIENCE SOLIDWORKS Desktop → Full. The site hides the desktop options from a Linux browser. Step 7 sets up Firefox if you need it for the download too. Sign in normally with your own account.

The full ZIP is about 28 GB. You'll also need room for the extracted media, the separate Design download, the installed CAD, prerequisites and temp files. Keep all of it outside this repo.

Install the host tools the scripts use and the ones needed to rebuild the small Windows helpers:

```bash
sudo pacman -S --needed git python firefox clang lld wine unzip cabextract curl
```

Host `wine` is only here for its import libraries, which the builds below link against. Run the app itself with the pinned Proton Wine, not `/usr/bin/wine`. Check these libraries exist before compiling:

```bash
ls /usr/lib/wine/x86_64-windows/lib{kernel32,ntdll,user32,comctl32,msi}.a
```

To use the same UMU, download `umu-launcher-1.4.4-zipapp.tar` from the [official 1.4.4 release](https://github.com/Open-Wine-Components/umu-launcher/releases/tag/1.4.4), extract `umu-run` into `~/.local/bin` and make it executable. The one I used has this SHA256:

```text
d0005a58602041229cc467dab03dc0c0b9e8cce09a8145b16b7683244cf17804
```

Install [UMU-Proton-10.0-4](https://github.com/Open-Wine-Components/umu-proton/releases/tag/UMU-Proton-10.0-4) under `~/.local/share/Steam/compatibilitytools.d/`. On the reference machine, UMU downloaded and verified it for me. My DLL guard is pinned to this release, so a newer Proton is its own experiment. UMU manages the Steam runtime, so what it downloads today might not match the sniper build I recorded.

## 2. Set up the isolated environment

From the cloned SM4L directory, and in the same terminal for everything below:

```bash
export SM4L_ROOT="$PWD"
export SOLIDWORKS_PROTON_STATE="$HOME/.local/share/solidworks-proton"
export PROTONPATH="$HOME/.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4"
export UMU_RUN="$HOME/.local/bin/umu-run"
export PROTON_NO_FSYNC=1 PROTON_NO_ESYNC=1 PROTON_USE_XALIA=0
export PROTON_VERB=run WINEDEBUG=-all
export WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix" GAMEID=umu-default
mkdir -p "$SOLIDWORKS_PROTON_STATE"
chmod +x launch_proton.sh open_windows_firefox.sh
./launch_proton.sh --check
```

Use your current session's `DISPLAY`, `XAUTHORITY` and, if you have it, `WAYLAND_DISPLAY`. Run from a normal terminal in that session. Don't copy the reference machine's `/run/user/.../xauth_*` filename over to another machine.

`launch_proton.sh` starts the persistent Wine server on the host before UMU builds its container. It raises the soft descriptor limit to the hard limit and keeps fsync/esync off. Every launch into this prefix has to use the same Proton and sync settings.

Initialize the fresh prefix through the launcher:

```bash
./launch_proton.sh "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0
```

Nobody has run a fresh initialization with this final launcher on another machine yet. Check that `$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c` exists before moving on. On the reference machine, `prefix/pfx` is a symlink to `.`. Don't make a second, unrelated Wine prefix.

For registry commands and native probes, define this helper once the prefix exists:

```bash
pwine() {
  env WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" \
    WINEFSYNC=0 WINEESYNC=0 WINEDEBUG=-all \
    "$PROTONPATH/files/bin/wine64" "$@"
}
```

If the prefix already has a server running inside the container, close its CAD processes first and stop only that prefix's server, once:

```bash
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Then start it again with `launch_proton.sh`. Don't kill other Wine prefixes or a session with unsaved work.

## 3. Install real .NET and use Windows 11 for the installer

With the host server from initialization still running:

```bash
"$UMU_RUN" winetricks -q dotnet48
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
./launch_proton.sh "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32/winecfg.exe" -v win11
pwine 'C:\windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe' /?
```

The .NET recipe has to actually install the 64-bit RegAsm tool. On the reference machine, the media's own .NET 4.8.1 DISM installer reported success without installing it, and Login Manager registration still failed. Winetricks' .NET 4.8 recipe fixed it. Stop the prefix's server after the recipe, because Winetricks can restart it inside the container. The next launcher call brings back the host server, and the winecfg call puts Windows 11 back after Winetricks changes it. After that, the vendor's Login Manager registration returned zero.

## 4. Install the platform with the IE10 and dictionary fixes

Extract your full vendor ZIP into the state directory. Point `MEDIA_1` at the folder with `setup.exe`, `setup_noUAC.exe` and `media.db`:

```bash
export MEDIA_1="$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1"
python3 -B test_patch_offline_installer.py "$MEDIA_1"
python3 patch_offline_installer.py "$MEDIA_1/setup.exe"
./launch_proton.sh "$MEDIA_1/setup_admin_proton_offline.exe"
```

The patch checks the whole file's hash, then changes only the IE10 export check, in a separately named copy. All it does is skip a false prerequisite check for the missing `HttpWebSocketReceive`. It doesn't implement WebSockets. The original media isn't touched, and the patched copy's signature is no longer valid.

Use the normal administrator entry point. `setup_noUAC.exe` ran into a vendor elevation error.

**On the reference machine I actually selected W4Y (3DEXPERIENCE SOLIDWORKS Ultimate)**, default install directory, updates on demand. The same prefix later launched **Professional for Makers** with my account's license, and I didn't reinstall as Professional. `XWB` is the separate Professional option in the installer records, but I haven't tested that route on a fresh install. If you want an exact replay, pick W4Y. That isn't an entitlement to a different license tier.

Default platform location:

```bash
export PLATFORM_BIN="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS 3DEXPERIENCE R2026x/win_b64/code/bin"
```

The first install failed at Object Modeler dictionary compilation, because the installed `CATSysTS.dll` looks up an `RtlIsNameInExpression` that isn't there. After that first install stops, apply my matcher:

```bash
python3 -B test_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll"
python3 -B apply_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll"
```

This uses the checked-in `swcompat.dll`, saves `CATSysTS.dll.pre-swcompat`, and rewrites only the KERNEL32 import provider. The proxy forwards everything that already exists and adds real length-delimited Unicode/DOS wildcard matching when NTDLL doesn't have it.

The installer's **Restart installation** copies the original DLL back. Before you hit Restart, run this in a second terminal with the same environment:

```bash
python3 -B apply_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll" --watch-for-recopy
```

The watcher waits up to 15 minutes for the exact original bytes to reappear, then patches them again. On the reference machine, the dictionary compiler then returned zero, wrote a 190,218-byte dictionary, and the platform install finished. This step installs the platform, connector and Installation Manager. CAD comes separately in step 5.

If you'd rather rebuild the proxy than use the checked-in one:

```bash
python3 -B build_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll.pre-swcompat" "$SOLIDWORKS_PROTON_STATE/directory-compat-build"
```

Then pass `--shim <build-directory>/swcompat.dll` to the apply script. The build output directory must not exist yet. Every guarded patch refuses builds it doesn't know. Keep the hash check.

## 5. Install the actual SOLIDWORKS Design CAD payload

Use the vendor Installation Manager to download **SOLIDWORKS Design 2026 SP3.0** and its prerequisites. Keep its full `PreReqs`, `Toolbox` and `swwi` download folders. On the reference machine, the manager downloaded and ran the prerequisites, then the CAD MSI's ZIP step failed.

The manager cache and CAD install paths I tested use Proton's default `steamuser` profile:

```bash
export CAD_DATA="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/users/steamuser/Downloads/3DEXPERIENCE SOLIDWORKS Downloads/2026 SP3.0/swwi/data"
export CAD_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS"
```

`InstallSpatialIOP` failed because the Windows ZIP-shell API returned `0x8000ffff`. So I extracted the real `spatialiop.zip` myself, checked every entry's CRC and size, and turned off only that extraction step in a separate copy of the MSI:

```bash
python3 -B test_prepare_design_install.py
python3 prepare_design_install.py "$CAD_DATA" "$CAD_DIR"
clang --target=x86_64-pc-windows-msvc -O2 -Wall -Wextra -Werror -fno-builtin \
  -c cad-msi-experiment.c -o "$SOLIDWORKS_PROTON_STATE/cad-msi.obj"
lld-link /entry:entry /subsystem:console /nodefaultlib /machine:x64 \
  "/out:$SOLIDWORKS_PROTON_STATE/cad-msi.exe" "$SOLIDWORKS_PROTON_STATE/cad-msi.obj" \
  /usr/lib/wine/x86_64-windows/libkernel32.a /usr/lib/wine/x86_64-windows/libmsi.a
./launch_proton.sh "$SOLIDWORKS_PROTON_STATE/cad-msi.exe"
```

The C helper is the exact install I ran, with the Windows cache and install paths above hard-coded. It checks the custom action's target, sets `InstallSpatialIOP`'s condition to `0`, and calls `MsiInstallProductW`. The properties I tested include `ADDLOCAL=ALL`, `OFFICEOPTION=3`, `SWXIM=1`, `SLDIM=1`, the default Toolbox folder, and no reboot. Don't use it with another release, or before the real ZIP is extracted.

The payload had 11,547 ZIP entries and 2,048,172,990 bytes unpacked. An earlier optional-feature list taken from the manager returned success without installing the CAD core. `ADDLOCAL=ALL` installed the real `sldworks.exe`. The log from the run that worked is `C:\sw-design-preextracted.log`. A UMU supervisor can stay alive afterwards because vendor services keep running. Check the MSI's result and the executable itself, not whether that supervisor exited.

```bash
ls "$CAD_DIR/sldworks.exe"
```

## 6. Install and configure WebView2

Download Microsoft's x64 Evergreen standalone installer from its [official link](https://go.microsoft.com/fwlink/p/?LinkId=2124701). On the reference machine the installer's hash was `ac22ecdc19c5b88b87f3fa752c00da9541653a8f5c0c5fc4a3b2b6ebe6591f69` and it installed runtime `154.0.4258.62`. The Evergreen link changes over time, so a newer runtime is a difference worth writing down, not an exact match.

```bash
./launch_proton.sh "$SOLIDWORKS_PROTON_STATE/MicrosoftEdgeWebView2RuntimeInstallerX64.exe" /silent /install
```

Check that the real `msedgewebview2.exe` exists under `drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/<version>/` and that the EdgeUpdate registration shows `pv` and `LastInstallerError=0`. The vendor's loader DLL on its own isn't enough.

Keep Proton's existing `msedgewebview2.exe` `Version=win7` override. I tried `win11`, it didn't fix the startup failures, and I put `win7` back. That's just what worked here. It's not Microsoft saying WebView2 supports Windows 7.

Use Wine's builtin D3D libraries for the embedded runtime only:

```bash
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v dxgi /t REG_SZ /d builtin /f
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v d3d11 /t REG_SZ /d builtin /f
```

The login page rendered once I set these **HKLM** policies for the two vendor executables. Elevated WebView startup ignored environment and HKCU arguments when I tried them:

```bash
export WEBVIEW_FLAGS='--enable-logging --v=1 --log-file=C:\webview-blank.log --use-gl=angle --use-angle=swiftshader'
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v ENOPLMCSAClient.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v SWXDesktopLauncher.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
```

That log can contain sign-in URLs and tickets, so keep it local. I didn't use `--no-sandbox` or any web-security bypass. SwiftShader only renders the embedded login. It has nothing to do with CAD's OpenGL setting.

## 7. Use a Windows-identifying Firefox profile for login

Set your own HTTPS 3ds.com platform URL. The repo doesn't include my tenant or dashboard IDs:

```bash
export SOLIDWORKS_PLATFORM_URL='https://YOUR-PLATFORM-HOST.3dexperience.3ds.com/'
python3 -B launch_windows_browser.py
```

The helper sets up a dedicated `browser-windows-firefox` profile, checks its real HTTP User-Agent and JavaScript navigator fields against a local page, then opens the platform. Sign in yourself. The helper stays running until Firefox closes. Close this browser before rerunning the profile setup, and leave your other Firefox profiles alone.

The Windows user-agent alone wasn't enough in my earlier attempts. I needed Firefox's user-agent, platform (`Win32`), OS and app-version overrides all together. After that, SOLIDWORKS Design showed up in the browser.

Send only this Wine prefix's login links to the dedicated profile:

```bash
pwine reg.exe add 'HKCU\Software\Wine\WineBrowser' /v Browsers /t REG_SZ /d "$SM4L_ROOT/open_windows_firefox.sh" /f
```

The handler uses UMU's `steam-runtime-launch-client --host --` to open Firefox outside the container. It's only for links coming from inside UMU, not a general way to launch a host browser. Keep the checkout at the registered path, or update this registry value if you move it. Your normal Linux browser defaults don't change.

## 8. Check the vendor launcher and normal sign-in

The website looks for the installed Windows `3DEXPERIENCELauncher` service. A connected browser isn't enough on its own. With the desktop environment available:

```bash
pwine sc.exe query 3DEXPERIENCELauncher
pwine sc.exe start 3DEXPERIENCELauncher
curl --head --max-time 5 http://127.0.0.1:20250/
```

On the reference machine the HTTP check returned 200. If the service is already running, another start can be rejected, so query it and check the endpoint before assuming it failed. I had to stop and restart it once when it accepted TCP but never answered HTTP.

Next, mark the launcher service as interactive. This is the fix that finally made platform launches show up on screen:

```bash
pwine reg.exe add 'HKLM\System\CurrentControlSet\Services\3DEXPERIENCELauncher' /v Type /t REG_DWORD /d 0x110 /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Wine starts every service on a hidden desktop (`__wineservice_winstation\Default`) unless the service has the `SERVICE_INTERACTIVE_PROCESS` flag (`0x100`). The vendor service is `0x10`, so the launcher backbone it creates, and every CAD copy that backbone starts, ran with no display at all. CAD got its license and kept running, but you'd never see a window. `0x110` keeps the original own-process type and adds the interactive flag. Close CAD before stopping the prefix, because the flag only applies when the service starts again.

Before I found this, I was swapping the service's headless backbone for an interactive copy with the same named-pipe arguments by hand. That doesn't hold up. The service starts a new backbone for every request, so the swap had to happen on every launch. [The handoff notes](FINDINGS.md#browser-to-launcher-handoff) describe that old recovery.

If the website stalls, start the real tray interactively:

```bash
export LAUNCHER_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/3DEXPERIENCE Launcher"
./launch_proton.sh "$LAUNCHER_DIR/3DEXPERIENCELauncherSysTray.exe"
```

Then click **Open once** and watch for the vendor's normal trusted-platform prompt.

I also replayed a fresh signed-in SWXDesktopLauncher request interactively without changing its arguments. Never commit, log or reuse those URLs or tickets on another machine. Starting `sldworks.exe` directly doesn't skip the platform. CAD hands off to `SWXDesktopLauncher`, asks you to open 3DEXPERIENCE in the browser and click **Open**, then the service starts CAD again. That second copy is the one you use, which is why the service has to be interactive.

Before the run that worked, I hit server-access errors, HTTP 403 and license error 1002. I don't know exactly what resolved them. Don't assume a purchased role is assigned, and don't patch a license result. If those errors come back, check your account, tenant and assigned role.

## 8b. Install the background units

**Verified** on the reference machine, with the units enabled as described below. The browser's Open button needs the launcher unit, and it does nothing useful without it.

The unit files in `units/` contain the path of the author's checkout. Copy them into your user unit directory and point them at your own checkout:

```bash
mkdir -p ~/.config/systemd/user
for u in units/*.service; do
  sed "s#%h/AI/System/Work-Laptop/apps/solidworks/SM4L#$SM4L_ROOT#g" "$u" > ~/.config/systemd/user/"$(basename "$u")"
done
systemctl --user daemon-reload
systemctl --user enable --now sm4l-launcher.service
```

- `sm4l-launcher.service` boots the prefix's 3DEXPERIENCE launcher tray at login, so `127.0.0.1:20250` answers before you click Open. Restart it after a KWin restart, because `XAUTHORITY` changes then.
- `sm4l-spacemouse.service` and `sm4l-ui-compat.service` run persistent bridges. They attach to any new `sldworks.exe`, so CAD started from the browser's Open gets the add-ins too. Enable the SpaceMouse unit once you've set up the driver from [SpaceMouse on Linux](SPACEMOUSE.md). Enable `sm4l-ui-compat.service` as well, since it carries the header fix and off-screen dialog recovery.
- Exit code 2 means another bridge already holds the prefix lock. The units don't restart on that code.

The launcher unit sets `SM4L_SPACEMOUSE=0` and `SM4L_UI_COMPAT=0` for its own tray start, because the bridge units own the add-in loaders.

## 9. Apply the CAD header-control crash fix

Before opening CAD, patch the prefix's amd64 copy of Wine's Common Controls:

```bash
export HEADER_DLL="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/winsxs/amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.0.2600.2982_none_deadbeef/comctl32.dll"
python3 -B test_patch_header_layout.py "$HEADER_DLL"
python3 patch_header_layout.py "$HEADER_DLL"
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v comctl32 /t REG_SZ /d native,builtin /f
```

The supported Wine DLL hash is `d0616fbdb1649047ac7f0fea3a55f8ab70b33b4c0703c056a6706c43c0cf1676`. The patch saves `comctl32.before-header-guard.dll` next to it. It catches a null `HDM_LAYOUT` pointer and returns FALSE, and valid layouts still run the original code. It also changes the local Wine builtin marker so Wine loads this copy instead of redirecting to Proton's shared DLL. The override only applies to `sldworks.exe`, and Proton's shared files stay untouched.

A prefix refresh can copy the original back. If startup crashes again, compare the current DLL with the backup and only rerun the guard on the matching original. Running it on an already-patched file is refused on purpose.

## 9b. Use classic controls so the checkbox and radio labels draw

**Verified** on the reference machine on 2026-10-08. With the prefix's Windows theme on, SOLIDWORKS' PropertyManager checkboxes and radio buttons draw without their labels. Turning the theme off makes SOLIDWORKS use classic controls, and the labels render. The cost is a flatter, classic look, which is an acceptable trade for this setup.

Close CAD and stop the prefix first. Then back up the prefix's registry and set the theme value:

```bash
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/user.reg" "$SOLIDWORKS_PROTON_STATE/user.reg.before-theme-off"
pwine reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\ThemeManager' /v ThemeActive /t REG_SZ /d 0 /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Stop the prefix after the `reg add`. `pwine` starts its own wineserver, which writes `user.reg` when it exits. The `wineserver -k` line makes sure that write happens before the next launch.

Start CAD as usual. You don't need the UI-compat helper for the labels.

Proton doesn't rewrite this value on a normal start. A prefix update or a recreated prefix resets it, so run this step again after either one.

**Pending a live test:** `launch_proton.sh` calls `ensure_theme_off.py` before every start, which re-applies `ThemeActive=0` automatically, including after a prefix update. Its tests pass on a copy, but it hasn't been confirmed in a real start yet. Until it is, re-running this step after a prefix update is the fallback.

To roll back, close CAD, stop the prefix and restore the backup:

```bash
cp "$SOLIDWORKS_PROTON_STATE/user.reg.before-theme-off" "$SOLIDWORKS_PROTON_STATE/prefix/pfx/user.reg"
```

That restores the whole `user.reg`, so it also undoes any other registry changes made since the backup. If you only want to switch the theme back on, set `ThemeActive` to `1` instead. The original value was `1`, with `DllName` pointing at `light.msstyles`.

## 9c. Use native msxml6 for CAD so 3MF Save As works

**Verified once.** On 2026-10-08 at about 14:35: Save As 3MF completed, CAD started cleanly with no popups, and the file imported into PrusaSlicer. Keep this to one run until it has passed again on another retry.

Without this, 3MF Save As crashes CAD. The builtin msxml3 that Wine ships miscounts document references when nodes move between documents, so a later read reaches freed memory. Forcing native msxml6 for `sldworks.exe` avoids that path.

Stop the prefix first. Then back up the registry and the msxml6 files:

```bash
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/user.reg" "$SOLIDWORKS_PROTON_STATE/user.reg.before-msxml6"
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/system.reg" "$SOLIDWORKS_PROTON_STATE/system.reg.before-msxml6"
mkdir -p "$SOLIDWORKS_PROTON_STATE/msxml6-backup"
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32/msxml6.dll" "$SOLIDWORKS_PROTON_STATE/msxml6-backup/system32-msxml6.dll"
cp "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/syswow64/msxml6.dll" "$SOLIDWORKS_PROTON_STATE/msxml6-backup/syswow64-msxml6.dll"
```

Get Microsoft's MSXML 6.0 package, KB2957482. Winetricks downloads it from [Microsoft's download page](https://download.microsoft.com/download/2/7/7/277681BE-4048-4A58-ABBA-259C465B1699/msxml6-KB2957482-enu-amd64.exe) and caches it under `~/.cache/winetricks/msxml6/`. Check the file first:

```bash
sha256sum msxml6-KB2957482-enu-amd64.exe
# expected: 260cd870851ffc3c6d10b71691f134e20d8d03ac26073bb36951eacb7aa85897
```

Extract the installer, then the `.msi` it contains. The files inside are named by their MSI file key:

```bash
7z x -y msxml6-KB2957482-enu-amd64.exe
7z x -y msxml6.msi
```

The 64-bit and 32-bit builds are told apart by the key suffix. Copy each one to the name CAD expects:

```bash
MSXML_SRC="$PWD"
SYS32="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32"
SYSWOW="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/syswow64"
cp "$MSXML_SRC/msxml6.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB" "$SYS32/msxml6.dll"
cp "$MSXML_SRC/msxml6r.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB" "$SYS32/msxml6r.dll"
cp "$MSXML_SRC/msxml6.dll.86F857F6_A743_463D_B2FE_98CB5F727E09" "$SYSWOW/msxml6.dll"
cp "$MSXML_SRC/msxml6r.dll.86F857F6_A743_463D_B2FE_98CB5F727E09" "$SYSWOW/msxml6r.dll"
```

The expected SHA256 values, before you copy:

- `system32` (x64): `msxml6.dll` `6fb5aead277001403cd01178346253455cdb9926b69f12ee99764ae358d7b21b`, `msxml6r.dll` `6e476a37fcff8ceab3ea9d08b381cc42238b00ad50b0fd05250b621c4ecdbce2`
- `syswow64` (x86): `msxml6.dll` `66fb552089d28797ed74afbff5ab2c739828cf9abb10579a6641d5bd51cdec7b`, `msxml6r.dll` `c4c3e734abbf54424f878457d93e4981f0ef19cfa974aeeacddfa916a508b185`


The scripted path does the same copies, checks the hashes, and sets the override. With the prefix stopped, run `python3 -B install_msxml6.py` from the folder with the cached KB2957482 package. It needs `7z`. The manual steps below stay the reference.

Then set the override for CAD only, and stop the prefix again:

```bash
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v msxml6 /t REG_SZ /d native,builtin /f
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

To roll back, close CAD and stop the prefix. Restore the two backed-up `msxml6.dll` files, delete both `msxml6r.dll` files, and remove the `msxml6` value under `AppDefaults\sldworks.exe\DllOverrides`. Restoring the `user.reg` and `system.reg` backups also works.

## 10. Launch CAD and fix the black viewport

```bash
./launch_proton.sh "$CAD_DIR/sldworks.exe"
```

The reference machine window identified itself as **SOLIDWORKS Design Professional for Makers 2026 SP3.0 — For Personal Use Only**. Menus and the feature tree drew fine, but the part viewport and some content panes were black.

Go to **Tools → Options → System Options → Performance**, clear **Enhanced graphics performance (requires SOLIDWORKS restart)**, apply, close CAD normally, and start it again with the command above. The setting it saved on the reference machine was:

```text
HKCU\Software\SolidWorks\SOLIDWORKS 2026\Performance
Use Performance Pipeline 2020 = DWORD 0
```

I changed it in the GUI. **I didn't turn on software OpenGL**. It was greyed out before the change. After the restart I created a cube and chamfered it. The [vendor graphics guide](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P) walks through the same enhanced-graphics and software-OpenGL troubleshooting.

## 11. Install the start menu item

From the cloned checkout:

```bash
chmod +x launch_solidworks.sh
python3 -B install_desktop.py
desktop-file-validate "$HOME/.local/share/applications/SM4L-solidworks.desktop"
```

Search your app menu for **SOLIDWORKS for Makers**. The launcher uses this checkout's Proton wrapper, the installed CAD path and the working startup settings. It also starts the optional [SpaceMouse bridge](SPACEMOUSE.md). On the reference machine I validated the entry, refreshed KDE's menu cache with `kbuildsycoca6 --noincremental`, and launched CAD from it.

The entry points at the checkout's absolute path, so rerun the installer if you move the checkout. It uses `$XDG_DATA_HOME/applications` when `XDG_DATA_HOME` is set, so adjust the validation path to match. It's a user menu entry and doesn't need root.

## 12. Verify the new machine and record its checkpoint

Confirm which edition is actually running, that sketch planes show up, and that you can sketch, extrude, chamfer, rotate the model and exit normally. Save a test `.SLDPRT`, close CAD, reopen it, and check its features. Write down the GPU, package versions and anything that differs from `checkpoint.json`.

On the reference machine, these have been confirmed:

- Sketching, extruding, chamfering and rotating a cube.
- SpaceMouse navigation, including the view following the cap.
- Checkbox and radio labels in the PropertyManager, with the theme off (step 9b).
- The PropertyManager section headers, including through drag and resize (the header hook in the UI add-in).
- Save As 3MF, verified once (step 9c). The file imported into PrusaSlicer.

These are not confirmed yet:

- Saving a `.SLDPRT` and reopening it.
- The status-bar `SetWindowPos` dedupe in its default-on mode, which was measured in an A/B run but not yet verified after a restart.
- The leftover-process cleanup on a real CAD exit. Its tests pass, but it hasn't acted on a real exit yet.
- Embedded browser panels still flash. That's a separate problem from the CAD graphics setup.

Model rebuilds are slow on the reference machine. In measured runs, most of the time goes to Wine window-system calls, not to modeling. Treat speed as an open problem.

A splash screen or a running process doesn't count as a successful replication.

## Checks and rollback

These run against temp files and mock executables, without launching CAD:

```bash
python3 -B test_launch_proton.py
python3 -B test_spacemouse.py
python3 -B test_windows_browser.py
python3 -B test_open_windows_firefox.py
python3 -B test_prepare_design_install.py
python3 -B test_directory_compat.py
python3 -B test_cad_cleanup.py
python3 -B test_swp_dedupe.py
```

`test_install_msxml6.py` runs against a throwaway prefix and needs `7z`.

These need your matching original files:

```bash
python3 -B test_patch_offline_installer.py "$MEDIA_1"
python3 -B test_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll.pre-swcompat"
python3 -B test_patch_header_layout.py "$HEADER_DLL"
```

After patching, use the header backup as the test input. The directory check expects the checked-in proxy in the current directory.

`header_layout_probe.c`, `event_signal_probe.c` and `child_memory_probe.c` are the native API reproductions. Compile each with clang's Windows x64 target, then link with `/entry:entry /subsystem:console /nodefaultlib /machine:x64` against the import libraries it needs. The header probe needs kernel32, user32 and comctl32 plus a Common Controls v6 manifest dependency. The event and child-memory probes only need kernel32. The header probe's exact link options are:

```text
/manifestdependency:type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="amd64" publicKeyToken="6595b64144ccf1df" language="*"
/manifest:embed
```

Rolling back only touches this prefix. Close CAD normally first. Rename `CATSysTS.dll.pre-swcompat` and `comctl32.before-header-guard.dll` back to their original names as needed. To undo the settings, remove the `sldworks.exe/comctl32` and WebView `dxgi`/`d3d11` override values, the two HKLM WebView arguments, and the WineBrowser `Browsers` value. The original installer media and source MSI are never changed. Only turn Enhanced graphics performance back on in the GUI when you're deliberately testing that path again.

Keep runtime logs and dumps local, since they can contain credentials or launch URLs. This repo intentionally doesn't include the reference machine's installed prefix or the signed-in Firefox profile.

## UI compatibility helper

The menu launcher also starts the UI helper after the host Wine server. It builds our own add-in with the same clang/lld and Wine import libraries used for SpaceMouse support, but does not need a SpaceMouse or spacenavd. Checkbox and radio labels now come from step 9b, so the helper no longer un-themes controls. It brings fully off-screen owned dialogs back over the owner's window. The header hook in the same add-in fixes the section-header wipe. It was verified on 2026-10-08 in Fillet, including drag, resize and no flicker. The kill switches are `C:\sm4l-hdr-nozorder-off` and `C:\sm4l-hdr-clamp-off`, which turn off the z-order and width-pin parts so each can be tested alone.

For an already running CAD session:

```bash
python3 -B spacemouse.py --ui-only
```

Use the same prefix and Proton settings as the rest of this guide. To disable it for future menu launches, set SM4L_UI_COMPAT=0. An already loaded add-in stays until disabled in Tools → Add-Ins or CAD is restarted. Do not swap loaded DLL bytes expecting a hot reload. The helper does not select filenames, accept features, or press Save. Native KDE file chooser integration is still pending.
