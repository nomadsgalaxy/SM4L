# Replicate the laptop setup on Arch Linux

This is the route I took on the laptop, with the final working settings in one place. I haven't replayed it on a fresh prefix yet. That's next, on the desktop. Some steps go through the vendor GUI, and the handoff from the browser to the launcher needed manual recovery along the way.

## 1. Match the versions and get your own downloads

What I pinned:

- Arch Linux x86_64. Laptop renderer `Mesa Intel(R) Graphics (MTL)`.
- UMU 1.4.4 upstream zipapp, UMU-Proton-10.0-4, sniper runtime `3.0.20260928.262393`.
- Full platform media `SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip`.
- SOLIDWORKS Design 2026 SP3.0, MSI registered as `34.130.0150`.
- Microsoft .NET 4.8, installed through Proton's Winetricks recipe.
- Microsoft WebView2 x64 Evergreen runtime `154.0.4258.62`.

The exact laptop package versions and supported file hashes are in [checkpoint.json](../checkpoint.json). Your GPU and package versions will probably be different. Write them down before changing anything.

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

Install [UMU-Proton-10.0-4](https://github.com/Open-Wine-Components/umu-proton/releases/tag/UMU-Proton-10.0-4) under `~/.local/share/Steam/compatibilitytools.d/`. On the laptop, UMU downloaded and verified it for me. My DLL guard is pinned to this release, so a newer Proton is its own experiment. UMU manages the Steam runtime, so what it downloads today might not match the sniper build I recorded.

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

Use your current session's `DISPLAY`, `XAUTHORITY` and, if you have it, `WAYLAND_DISPLAY`. Run from a normal terminal in that session. Don't copy the laptop's `/run/user/.../xauth_*` filename over to another machine.

`launch_proton.sh` starts the persistent Wine server on the host before UMU builds its container. It raises the soft descriptor limit to the hard limit and keeps fsync/esync off. Every launch into this prefix has to use the same Proton and sync settings.

Initialize the fresh prefix through the launcher:

```bash
./launch_proton.sh "$PROTONPATH/files/lib/wine/x86_64-windows/cmd.exe" /c exit 0
```

Nobody has run a fresh initialization with this final launcher on another machine yet. Check that `$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c` exists before moving on. On the laptop, `prefix/pfx` is a symlink to `.`. Don't make a second, unrelated Wine prefix.

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

The .NET recipe has to actually install the 64-bit RegAsm tool. On the laptop, the media's own .NET 4.8.1 DISM installer reported success without installing it, and Login Manager registration still failed. Winetricks' .NET 4.8 recipe fixed it. Stop the prefix's server after the recipe, because Winetricks can restart it inside the container. The next launcher call brings back the host server, and the winecfg call puts Windows 11 back after Winetricks changes it. After that, the vendor's Login Manager registration returned zero.

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

**On the laptop I actually selected W4Y (3DEXPERIENCE SOLIDWORKS Ultimate)**, default install directory, updates on demand. The same prefix later launched **Professional for Makers** with my account's license, and I didn't reinstall as Professional. `XWB` is the separate Professional option in the installer records, but I haven't tested that route on a fresh install. If you want an exact replay, pick W4Y. That isn't an entitlement to a different license tier.

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

The watcher waits up to 15 minutes for the exact original bytes to reappear, then patches them again. On the laptop, the dictionary compiler then returned zero, wrote a 190,218-byte dictionary, and the platform install finished. This step installs the platform, connector and Installation Manager. CAD comes separately in step 5.

If you'd rather rebuild the proxy than use the checked-in one:

```bash
python3 -B build_directory_compat.py "$PLATFORM_BIN/CATSysTS.dll.pre-swcompat" "$SOLIDWORKS_PROTON_STATE/directory-compat-build"
```

Then pass `--shim <build-directory>/swcompat.dll` to the apply script. The build output directory must not exist yet. Every guarded patch refuses builds it doesn't know. Keep the hash check.

## 5. Install the actual SOLIDWORKS Design CAD payload

Use the vendor Installation Manager to download **SOLIDWORKS Design 2026 SP3.0** and its prerequisites. Keep its full `PreReqs`, `Toolbox` and `swwi` download folders. On the laptop, the manager downloaded and ran the prerequisites, then the CAD MSI's ZIP step failed.

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

Download Microsoft's x64 Evergreen standalone installer from its [official link](https://go.microsoft.com/fwlink/p/?LinkId=2124701). On the laptop the installer's hash was `ac22ecdc19c5b88b87f3fa752c00da9541653a8f5c0c5fc4a3b2b6ebe6591f69` and it installed runtime `154.0.4258.62`. The Evergreen link changes over time, so a newer runtime is a difference worth writing down, not an exact match.

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

On the laptop the HTTP check returned 200. If the service is already running, another start can be rejected, so query it and check the endpoint before assuming it failed. I had to stop and restart it once when it accepted TCP but never answered HTTP.

If the website stalls, start the real tray interactively:

```bash
export LAUNCHER_DIR="$SOLIDWORKS_PROTON_STATE/prefix/pfx/drive_c/Program Files/Dassault Systemes/3DEXPERIENCE Launcher"
./launch_proton.sh "$LAUNCHER_DIR/3DEXPERIENCELauncherSysTray.exe"
```

Then click **Open once** and watch for the vendor's normal trusted-platform prompt. On the laptop, the backbone the service created was headless, so I started the real `3DEXPERIENCELauncherBackbone.exe` interactively with **the current service's original named-pipe arguments**. Old pipe arguments stopped working after a service restart. Read [the handoff notes](FINDINGS.md#browser-to-launcher-handoff) before trying that. It's a manual recovery, not an automatic step yet.

I also replayed a fresh signed-in SWXDesktopLauncher request interactively without changing its arguments. Never commit, log or reuse those URLs or tickets on another machine. Once sign-in worked, I launched `sldworks.exe` directly from then on.

Before the run that worked, I hit server-access errors, HTTP 403 and license error 1002. I don't know exactly what resolved them. Don't assume a purchased role is assigned, and don't patch a license result. If those errors come back, check your account, tenant and assigned role.

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

## 10. Launch CAD and fix the black viewport

```bash
./launch_proton.sh "$CAD_DIR/sldworks.exe"
```

The laptop window identified itself as **SOLIDWORKS Design Professional for Makers 2026 SP3.0 — For Personal Use Only**. Menus and the feature tree drew fine, but the part viewport and some content panes were black.

Go to **Tools → Options → System Options → Performance**, clear **Enhanced graphics performance (requires SOLIDWORKS restart)**, apply, close CAD normally, and start it again with the command above. The setting it saved on the laptop was:

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

Search your app menu for **SOLIDWORKS for Makers**. The launcher uses this checkout's Proton wrapper, the installed CAD path and the working startup settings. It also starts the optional [SpaceMouse bridge](SPACEMOUSE.md). On the laptop I validated the entry, refreshed KDE's menu cache with `kbuildsycoca6 --noincremental`, and launched CAD from it.

The entry points at the checkout's absolute path, so rerun the installer if you move the checkout. It uses `$XDG_DATA_HOME/applications` when `XDG_DATA_HOME` is set, so adjust the validation path to match. It's a user menu entry and doesn't need root.

## 12. Verify the new machine and record its checkpoint

Confirm which edition is actually running, that sketch planes show up, and that you can sketch, extrude, chamfer, rotate the model and exit normally. Save a test `.SLDPRT`, close CAD, reopen it, and check its features. Write down the GPU, package versions and anything that differs from `checkpoint.json`.

On the laptop, the cube/chamfer and SpaceMouse navigation work. Save/reopen hasn't been tested yet. Embedded browser panels still flash, and that should be handled separately from the working CAD graphics setup. A splash screen or a running process doesn't count as a successful replication.

## Checks and rollback

These run against temp files and mock executables, without launching CAD:

```bash
python3 -B test_launch_proton.py
python3 -B test_spacemouse.py
python3 -B test_windows_browser.py
python3 -B test_open_windows_firefox.py
python3 -B test_prepare_design_install.py
python3 -B test_directory_compat.py
```

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

Keep runtime logs and dumps local, since they can contain credentials or launch URLs. This repo intentionally doesn't include the laptop's installed prefix or the signed-in Firefox profile.

## UI compatibility helper

The menu launcher also starts the UI helper after the host Wine server. It builds our own add-in with the same clang/lld and Wine import libraries used for SpaceMouse support, but does not need a SpaceMouse or spacenavd. It restores checkbox/radio labels through the classic painter and brings fully off-screen owned dialogs back over the owner's window. See [the findings](FINDINGS.md) for what was verified and what remains.

For an already running CAD session:

```bash
python3 -B spacemouse.py --ui-only
```

Use the same prefix and Proton settings as the rest of this guide. To disable it for future menu launches, set SM4L_UI_COMPAT=0. An already loaded add-in stays until disabled in Tools → Add-Ins or CAD is restarted. Do not swap loaded DLL bytes expecting a hot reload. The helper does not select filenames, accept features, or press Save. Native KDE file chooser integration is still pending.
