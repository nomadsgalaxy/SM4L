# Replicate the working laptop setup on Arch Linux

This is the route used on the laptop, with the final working settings collected in one place. Fresh-prefix replication on the desktop is pending. Some steps use the vendor GUI, and the browser-to-launcher handoff needed manual recovery during the investigation.

## 1. Match the versions and obtain your own downloads

The pinned components are:

- Arch Linux x86_64; laptop renderer `Mesa Intel(R) Graphics (MTL)`.
- UMU 1.4.4 upstream zipapp; UMU-Proton-10.0-4; sniper runtime `3.0.20260928.262393`.
- Full platform media `SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip`.
- SOLIDWORKS Design 2026 SP3.0, MSI registered as `34.130.0150`.
- Microsoft .NET 4.8 installed by Proton's Winetricks recipe.
- Microsoft WebView2 x64 Evergreen runtime `154.0.4258.62`.

Exact laptop package versions and supported file hashes are in [checkpoint.json](../checkpoint.json). The desktop GPU and installed package versions may differ; record them before changing anything.

If Linux hides the download, follow [Download the same installer from Linux](DOWNLOAD.md) first. It includes the tested Firefox identity setup, every download-menu step and media verification.

The vendor's full download was under Compass → All Apps → Members Control Center → Configure Apps Installation → 3DEXPERIENCE SOLIDWORKS Desktop → Full. The site hid desktop options with a Linux browser identity. Step 7 configures Firefox if you need it for the download too. Sign in normally with your own account.

The full ZIP was about 28 GB. Allow space for the extracted platform media, the separate Design download, installed CAD, prerequisites, and temporary files. Keep all of these outside this repository.

Install the host tools needed for the scripts and rebuilding the small Windows helpers:

```bash
sudo pacman -S --needed git python firefox clang lld wine unzip cabextract curl
```

Host `wine` supplies the import libraries used by the builds below. Run the application with the pinned Proton Wine, not `/usr/bin/wine`. Verify these library files exist before compiling:

```bash
ls /usr/lib/wine/x86_64-windows/lib{kernel32,ntdll,user32,comctl32,msi}.a
```

For the same UMU route, download `umu-launcher-1.4.4-zipapp.tar` from the [official 1.4.4 release](https://github.com/Open-Wine-Components/umu-launcher/releases/tag/1.4.4). Extract its `umu-run` into `~/.local/bin` and make it executable. The executable we used has SHA256:

```text
d0005a58602041229cc467dab03dc0c0b9e8cce09a8145b16b7683244cf17804
```

Install [UMU-Proton-10.0-4](https://github.com/Open-Wine-Components/umu-proton/releases/tag/UMU-Proton-10.0-4) under `~/.local/share/Steam/compatibilitytools.d/`. UMU downloaded and verified that release on the laptop. Our DLL guard is pinned to it; a newer Proton is a separate experiment. UMU manages the Steam runtime; its current download may differ from the recorded sniper build.

## 2. Set the isolated environment

From the cloned SM4L directory, use the same terminal for the steps below:

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

Use your current desktop session's `DISPLAY`, `XAUTHORITY` and, where present, `WAYLAND_DISPLAY`. Run from a normal terminal in that session. Do not copy the laptop's `/run/user/.../xauth_*` filename to the desktop.

`launch_proton.sh` starts the persistent server on the host before UMU makes a container. It raises the soft descriptor limit to the existing hard limit and keeps fsync/esync off. Every launch into this prefix must use the same Proton and synchronization settings.

Initialize the fresh prefix through the launcher:

```bash
./launch_proton.sh "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0
```

Fresh initialization with this final launcher has not yet been replayed on another machine. Confirm that `$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c` exists before continuing. On the laptop, `prefix/pfx` is a symlink to `.`; do not create a second unrelated Wine prefix.

For registry commands and native probes, define this helper after initialization:

```bash
pwine() {
  env WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" \
    WINEFSYNC=0 WINEESYNC=0 WINEDEBUG=-all \
    "$PROTONPATH/files/bin/wine64" "$@"
}
```

If this prefix already has a container-owned server, close its CAD processes first and stop only that prefix's server once:

```bash
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
```

Then use `launch_proton.sh` to start it again. Do not kill unrelated Wine prefixes or a session with unsaved work.

## 3. Install real .NET and use Windows 11 for the installer

With the initialized host server still running:

```bash
"$UMU_RUN" winetricks -q dotnet48
WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
./launch_proton.sh "$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/system32/winecfg.exe" -v win11
pwine 'C:windowsMicrosoft.NETFramework644.0.30319RegAsm.exe' /?
```

The .NET recipe must actually install the 64-bit RegAsm tool. On the laptop, the media's .NET 4.8.1 DISM installer returned success without supplying it; that attempt did not fix Login Manager registration. Winetricks' .NET 4.8 recipe did. Stop this prefix’s server after the recipe, since Winetricks can restart it inside the container. The next launcher call restores the host server and Windows 11 after Winetricks changes the Windows profile. The vendor Login Manager registration subsequently returned zero.

## 4. Install the platform with the IE10 and dictionary fixes

Extract your full vendor ZIP into the state directory. Set `MEDIA_1` to the extracted directory containing `setup.exe`, `setup_noUAC.exe` and `media.db`:

```bash
export MEDIA_1="$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1"
python3 -B test_patch_offline_installer.py "$MEDIA_1"
python3 patch_offline_installer.py "$MEDIA_1/setup.exe"
./launch_proton.sh "$MEDIA_1/setup_admin_proton_offline.exe"
```

The patch verifies the whole source hash and changes only the IE10 export-presence branch in a separately named copy. It skips a false prerequisite check for missing `HttpWebSocketReceive`; it does not implement WebSockets. The original media stays unchanged, and the changed copy's original signature is invalid.

Use the normal administrator entry point. The `setup_noUAC.exe` path hit a vendor elevation error.

**The actual laptop selection was W4Y — 3DEXPERIENCE SOLIDWORKS Ultimate**, default installation directory, updates on demand. The same prefix later launched **Professional for Makers** with the account's license. We did not reinstall Professional. `XWB` is the separate Professional choice shown in the installer records, but that fresh route is untested. For an exact replay, record the W4Y selection; do not treat it as entitlement to a different license tier.

Default platform location:

```bash
export PLATFORM_BIN="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS 3DEXPERIENCE R2026x/win_b64/code/bin"
```

The first install failed at Object Modeler dictionary compilation because the installed `CATSysTS.dll` looked up an absent `RtlIsNameInExpression`. Apply our real matcher after that first interrupted installation:

```bash
python3 -B test_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll"
python3 -B apply_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll"
```

This uses our checked-in `swcompat.dll`, preserves `CATSysTS.dll.pre-swcompat`, and rewrites only the KERNEL32 import provider. The proxy forwards existing imports and supplies actual length-delimited Unicode/DOS wildcard matching when the real NTDLL export is absent.

The vendor's **Restart installation** recopies the original DLL. Before choosing Restart, run this in a second terminal with the same environment:

```bash
python3 -B apply_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll" --watch-for-recopy
```

The watcher waits up to 15 minutes for the exact supported original bytes, then reapplies the change. On the laptop, the dictionary compiler returned zero, generated a 190,218-byte dictionary, and the platform installer completed successfully. This platform installation includes the connector and Installation Manager; CAD is installed separately in step 5.

To rebuild our proxy instead of using the checked-in one:

```bash
python3 -B build_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll.pre-swcompat" "$SOLIDWORKS_PROTON_STATE/directory-compat-build"
```

Use `--shim <build-directory>/swcompat.dll` with the apply script. The build output directory must not already exist. All guarded patches refuse unsupported builds; keep the hash check.

## 5. Install the actual SOLIDWORKS Design CAD payload

Use the vendor Installation Manager to download **SOLIDWORKS Design 2026 SP3.0** and its prerequisites. Keep its complete `PreReqs`, `Toolbox` and `swwi` download directories. The manager downloaded and ran prerequisites before the CAD MSI's ZIP action failed on the laptop.

The tested manager cache and CAD installation paths use the default Proton `steamuser` profile:

```bash
export CAD_DATA="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/users/steamuser/Downloads/3DEXPERIENCE SOLIDWORKS Downloads/2026 SP3.0/swwi/data"
export CAD_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/SOLIDWORKS Apps 2026/SOLIDWORKS"
```

`InstallSpatialIOP` failed because the Windows ZIP-shell API returned `0x8000ffff`. We extracted the real `spatialiop.zip`, checked every entry's CRC and size, and changed only that extraction action's condition in a separate MSI copy:

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

The C helper is the exact pinned installation experiment, with the Windows cache and installation paths above hard-coded. It validates the custom action's target, sets `InstallSpatialIOP`'s condition to `0`, and invokes `MsiInstallProductW`. Its tested properties include `ADDLOCAL=ALL`, `OFFICEOPTION=3`, `SWXIM=1`, `SLDIM=1`, the default Toolbox folder, and reboot suppression. Do not use it with another release or before real ZIP extraction.

The payload had 11,547 ZIP entries and 2,048,172,990 expanded bytes. An earlier manager-derived optional-feature list returned success without installing the CAD core. `ADDLOCAL=ALL` installed the actual `sldworks.exe`. The successful MSI log is `C:sw-design-preextracted.log`. A UMU supervisor can remain alive because vendor services remain running; check the MSI's result and the actual executable, not just that supervisor.

```bash
ls "$CAD_DIR/sldworks.exe"
```

## 6. Install and configure WebView2

Download Microsoft's x64 Evergreen standalone installer from its [official distribution link](https://go.microsoft.com/fwlink/p/?LinkId=2124701). On the laptop the installer hash was `ac22ecdc19c5b88b87f3fa752c00da9541653a8f5c0c5fc4a3b2b6ebe6591f69` and it installed runtime `154.0.4258.62`. The Evergreen link changes; a new runtime is a version difference to record, not a matching reproduction.

```bash
./launch_proton.sh "$SOLIDWORKS_PROTON_STATE/MicrosoftEdgeWebView2RuntimeInstallerX64.exe" /silent /install
```

Verify the real `msedgewebview2.exe` exists under `drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/<version>/` and the EdgeUpdate registration reports `pv` and `LastInstallerError=0`. The vendor loader DLL alone is insufficient.

Keep Proton's existing `msedgewebview2.exe` `Version=win7` override. We tried `win11`, which did not fix the startup failures, then restored `win7`. This records observed compatibility behavior, not Microsoft's support for WebView2 on Windows 7.

Use Wine's builtin D3D libraries for this embedded runtime only:

```bash
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v dxgi /t REG_SZ /d builtin /f
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe\DllOverrides' /v d3d11 /t REG_SZ /d builtin /f
```

The login renderer worked with these **HKLM** policies for the two vendor executables. Elevated WebView startup ignored environment/HKCU arguments during our investigation:

```bash
export WEBVIEW_FLAGS='--enable-logging --v=1 --log-file=C:\webview-blank.log --use-gl=angle --use-angle=swiftshader'
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v ENOPLMCSAClient.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
pwine reg.exe add 'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments' /v SWXDesktopLauncher.exe /t REG_SZ /d "$WEBVIEW_FLAGS" /f
```

The log can contain authentication URLs and tickets. Keep it local. No `--no-sandbox` or web-security bypass was used. SwiftShader rendered the embedded login; it is separate from CAD's OpenGL graphics setting.

## 7. Use a Windows-identifying Firefox profile for login

Set your own HTTPS 3ds.com platform URL. The repository does not include the laptop's tenant or dashboard identifiers:

```bash
export SOLIDWORKS_PLATFORM_URL='https://YOUR-PLATFORM-HOST.3dexperience.3ds.com/'
python3 -B launch_windows_browser.py
```

The helper configures a dedicated `browser-windows-firefox` profile, checks its actual HTTP User-Agent and JavaScript navigator fields against a local page, then opens the platform. Sign in yourself. Its process stays running until Firefox closes. Close this dedicated browser before rerunning the profile setup; leave unrelated Firefox profiles alone.

The Windows user-agent alone was insufficient during earlier attempts. We used Firefox's native user-agent, platform (`Win32`), OS and app-version overrides together. SOLIDWORKS Design then appeared in the browser.

Route only this Wine prefix's external login links to the dedicated profile:

```bash
pwine reg.exe add 'HKCU\Software\Wine\WineBrowser' /v Browsers /t REG_SZ /d "$SM4L_ROOT/open_windows_firefox.sh" /f
```

The handler calls UMU's `steam-runtime-launch-client --host --` to open Firefox outside the container. It is for browser links originating inside UMU; it is not a general host browser launcher. Keep the checkout at the registered path, or update this registry value when moving it. Normal Linux browser defaults are unchanged.

## 8. Check the vendor launcher and normal authentication

The website detects the installed Windows `3DEXPERIENCELauncher` service. A connected browser alone is not enough. With the desktop environment present:

```bash
pwine sc.exe query 3DEXPERIENCELauncher
pwine sc.exe start 3DEXPERIENCELauncher
curl --head --max-time 5 http://127.0.0.1:20250/
```

On the working laptop the HTTP check returned 200. An already-running service may reject another start; query and check the endpoint instead of assuming failure. We stopped and restarted this service once when its listener accepted TCP but did not return HTTP.

If the website stalls, start the real tray interactively:

```bash
export LAUNCHER_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/3DEXPERIENCE Launcher"
./launch_proton.sh "$LAUNCHER_DIR/3DEXPERIENCELauncherSysTray.exe"
```

Then click **Open once** and look for the vendor's normal trusted-platform confirmation. During the laptop investigation, a service-created backbone was headless; we started its real `3DEXPERIENCELauncherBackbone.exe` interactively with the **current service's original named-pipe arguments**. Old pipe arguments failed after a service restart. See [the handoff record](FINDINGS.md#browser-to-launcher-handoff) before attempting that recovery. This manual recovery is not yet a portable automatic step.

We also replayed a fresh authenticated SWXDesktopLauncher request interactively without changing its arguments. Never commit, log, or reuse those URLs/tickets on the desktop. Once login worked, the final CAD launches used `sldworks.exe` directly.

We saw server-access errors, HTTP 403 and license error 1002 before the successful run. Their exact resolution is not established. Do not infer that a purchased role is assigned, or patch a license result. Check the normal account, tenant and assigned role if those errors recur.

## 9. Apply the CAD header-control crash fix

Before opening CAD, patch the prefix's amd64 Wine Common Controls copy:

```bash
export HEADER_DLL="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/windows/winsxs/amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.0.2600.2982_none_deadbeef/comctl32.dll"
python3 -B test_patch_header_layout.py "$HEADER_DLL"
python3 patch_header_layout.py "$HEADER_DLL"
pwine reg.exe add 'HKCU\Software\Wine\AppDefaults\sldworks.exe\DllOverrides' /v comctl32 /t REG_SZ /d native,builtin /f
```

The supported Wine DLL hash is `d0616fbdb1649047ac7f0fea3a55f8ab70b33b4c0703c056a6706c43c0cf1676`. The patch preserves `comctl32.before-header-guard.dll` beside it. It guards a null `HDM_LAYOUT` pointer and returns FALSE; valid layouts still execute the original code. The local Wine builtin marker is changed so Wine can load this copy instead of redirecting to the shared Proton DLL. The override is limited to `sldworks.exe`; shared Proton files are unchanged.

A prefix refresh can recopy the original. If startup crashes again, compare the current DLL with the backup and rerun the guard only on the matching original. Running the patch on an already-patched file is intentionally refused.

## 10. Launch CAD and fix the black viewport

```bash
./launch_proton.sh "$CAD_DIR/sldworks.exe"
```

The running laptop window identified itself as **SOLIDWORKS Design Professional for Makers 2026 SP3.0 — For Personal Use Only**. Its menus and feature tree rendered, but the part viewport and some content panes were black.

In **Tools → Options → System Options → Performance**, clear **Enhanced graphics performance (requires SOLIDWORKS restart)**, apply, close CAD normally, and restart with the command above. The exact persisted laptop setting was:

```text
HKCU\Software\SolidWorks\SOLIDWORKS 2026\Performance
Use Performance Pipeline 2020 = DWORD 0
```

We changed this through the GUI. **Use software OpenGL was not enabled**; it was greyed out before the change. After restart, Anthony created a cube and chamfered it. The [vendor graphics guide](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P) describes the enhanced-graphics/software-OpenGL troubleshooting sequence.

## 11. Verify the desktop, then retain its checkpoint

Confirm the actual live edition, visible sketch planes, sketch creation, extrusion, chamfer, model rotation, and normal application exit. Save a test `.SLDPRT`, close CAD, reopen it, and verify its features. Record the GPU, package versions and any differences from `checkpoint.json`.

The laptop cube/chamfer is confirmed; save/reopen and SpaceMouse are pending. Browser elements still flash. Handle that separately from the working CAD graphics path. Do not call the desktop replication successful based on a splash screen or a running process alone.

## Checks and rollback

These checks use temporary files and mock executables, without launching CAD:

```bash
python3 -B test_launch_proton.py
python3 -B test_windows_browser.py
python3 -B test_open_windows_firefox.py
python3 -B test_prepare_design_install.py
python3 -B test_directory_compat.py
```

The source-dependent checks require your matching original files:

```bash
python3 -B test_patch_offline_installer.py "$MEDIA_1"
python3 -B test_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll.pre-swcompat"
python3 -B test_patch_header_layout.py "$HEADER_DLL"
```

Use the header backup as the test input after patching. The directory check expects the checked-in own proxy in the current directory.

`header_layout_probe.c`, `event_signal_probe.c` and `child_memory_probe.c` preserve the actual native API reproductions. Compile each with clang's Windows x64 target, then link `/entry:entry /subsystem:console /nodefaultlib /machine:x64` against the import libraries it needs. Header uses kernel32/user32/comctl32 plus a Common Controls v6 manifest dependency; event and child-memory use kernel32. The header's exact link option is:

```text
/manifestdependency:type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="amd64" publicKeyToken="6595b64144ccf1df" language="*"
/manifest:embed
```

Rollback changes only this prefix. Close CAD normally first. Restore `CATSysTS.dll.pre-swcompat` and `comctl32.before-header-guard.dll` to their original names as needed. Remove the `sldworks.exe/comctl32` and WebView `dxgi`/`d3d11` override values, the two scoped HKLM WebView arguments, and the WineBrowser `Browsers` value to undo those settings. Original installer media and source MSI remain unchanged. Re-enable Enhanced graphics performance through the GUI only when deliberately testing that path again.

Keep runtime logs and dumps local. They may contain credentials or launch URLs. This repository deliberately does not contain the laptop's installed prefix or authenticated Firefox profile.
