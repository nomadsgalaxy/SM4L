# What it took to get the laptop working

These are the experiments from October 6–7, 2026. The commands and final settings are collected in [REPLICATE.md](REPLICATE.md). Before this, I spent some time on native geometry experiments, but none of that was used to actually run SOLIDWORKS, so it's not in SM4L.

## Fixes that stuck

| What broke | What I found | What I kept |
| --- | --- | --- |
| Installer demands IE10 even with IE11 registry values | The bootstrap looks up a missing WinINet `HttpWebSocketReceive` export | A one-byte branch change in a separate copy of the offline setup, checked against the whole file's hash |
| Login Manager registration fails | The real Framework64 RegAsm was missing after the media's .NET 4.8.1 DISM attempt | Real Microsoft .NET 4.8 through Proton's Winetricks. Vendor registration then returns zero |
| Object Modeler dictionary compilation fails | CATSysTS looks up an NTDLL `RtlIsNameInExpression` that isn't there, and the compiler returns one | My proxy implements real Unicode/DOS wildcard matching. The compiler and the vendor install both return zero |
| CAD MSI can't unzip Spatial InterOp | ZIP-shell `SHCreateItemFromParsingName` fails with `0x8000ffff` | Extract the real ZIP with CRC/size checks and turn off only that redundant action in a separate MSI copy |
| MSI succeeds but there's no CAD core | The first optional-feature list left the core out | The direct MSI install uses `ADDLOCAL=ALL`, which installed the actual CAD executable |
| Linux browser hides the desktop app | A Windows label or user-agent on its own didn't bring the app back | Dedicated Firefox profile with a Windows user-agent plus Win32/Windows navigator overrides, verified live |
| CAD login opens the default Linux browser | WineBrowser sends links to the system browser | A prefix-only handler opens the dedicated Firefox profile on the host |
| WebView2 prerequisite error | The vendor loader exists, but the runtime and its registration don't | Installed Microsoft's real x64 Evergreen standalone runtime |
| WebView startup breakpoint | A restricted event handle has EVENT_MODIFY_STATE, but the fsync lookup also needs SYNCHRONIZE | Keep fsync/esync off. The event probe signals and sees the event |
| WebView GPU process launch error 39 | Native child-memory write returns 299, because the server's process_vm_writev returns EPERM across user namespaces | Start this prefix's persistent Wine server on the host before UMU. The allocate/write/read roundtrip then passes through UMU |
| Host server runs out of descriptors | The server inherited a limit of 2048 and hit it | Raise the soft limit to the existing hard limit before starting the server. The laptop's budget is 2097152 |
| Embedded login stays blank | DXVK divide-by-zero, and builtin D3D11/WARP has no usable renderer | Builtin D3D overrides for WebView only, plus HKLM SwiftShader arguments. The real login and error pages render |
| CAD crashes during UI startup | Two native CAD minidumps: access violation at COMCTL32+0x2ac1e reading address 8, a null HDLAYOUT | A prefix-local, version-pinned guard returns FALSE on null. The valid-layout probe still passes. The native,builtin override applies to CAD only |
| CAD opens with a black viewport | Menus, options and the feature tree render. Intel Mesa renderer, Enhanced graphics on | Turn off Enhanced graphics performance, apply and restart. After that I modeled a cube and chamfered it |

During the investigation, the directory matcher passed 191 expectation cases pulled independently from ReactOS's API tests. The repo's own check also covers DOS wildcards, Unicode, custom uppercase tables, import preservation, backup preservation, and refusing unsupported builds.

## Browser-to-launcher handoff

The website's Install/Open buttons depend on a lot at once: the real Windows launcher service, the installed apps, sign-in, browser identity, and the trusted-platform confirmation. Seeing those buttons doesn't prove CAD is licensed or visible.

The service is `3DEXPERIENCELauncher`, listening at `http://127.0.0.1:20250/`. At first it accepted TCP but hung on HTTP. Stopping and restarting it with the desktop environment available got HTTP 200 back. The tray also started with no X11 driver, so the backbone couldn't find the Windows `DSLauncherTray` window. Restarting the real tray interactively made the backbone's `postStatus` succeed, and SWXDesktopLauncher started.

After a reboot, the service's backbone could still come up headless. My manual recovery left the service alone and started the same vendor backbone interactively with its current named-pipe arguments:

1. Find the backbone that belongs to this prefix's service by its mapped executable, and confirm it has no winex11 mapping. Don't pick a backbone from another prefix or one that's already interactive.
2. Read that live process's NUL-separated `/proc/<pid>/cmdline` in memory. The argv I saw had three entries: the vendor executable and two pipe arguments. Don't print or save them.
3. Start the installed `3DEXPERIENCELauncherBackbone.exe` through the same Proton prefix and desktop environment, with those original argv entries after the executable, unchanged.
4. Keep the service and the interactive tray running, click Open once, and accept the normal vendor trust prompt. A restarted service gets a new pipe, so never reuse an old one.

Some fresh signed-in launches also needed an interactive replay. For the ENOPLMCSAClient child I saw, Wine had rewritten the argv: argv[0] was empty, argv[1] was `SWXDesktopLauncher`, the original launcher arguments sat in argv[2:16], argv[3] was `-Prfctx`, and argv[12] was `-RegistryUrl`. I kept those 14 original arguments in memory and started the platform's real SWXDesktopLauncher through my interactive launcher, leaving out the extra ENO arguments tacked on the end. That's what this one command layout looked like. It's not a general parser for other releases.

Those arguments carry private account and platform context plus launch tickets, so none of them are saved in SM4L. Replaying the laptop's arguments on the desktop would be wrong. If the same headless failure shows up there, capture a fresh request on that machine. This recovery still needs a proper, tested implementation. Once sign-in and the runtime fixes were in place, launching `sldworks.exe` directly worked.

## What I tried and dropped (or couldn't prove)

- Changing the IE registry numbers didn't supply the missing WinINet export.
- `setup_noUAC.exe` ran into the vendor's elevation requirement, so I used the normal administrator setup copy.
- The media's .NET 4.8.1 DISM install didn't supply RegAsm. I'm not claiming full .NET 4.8.1 support.
- A Windows 11 app override for WebView didn't fix startup, so I put Proton's original win7 override back.
- A fresh WebView user-data-folder policy didn't fix the blank panel. I removed it.
- A local headless DOM smoke test was inconclusive. The real evidence was the login and error pages rendering natively.
- I never showed that tenant casing caused the server-access error, so there's no casing patch.
- License error 1002 showed up, and I don't know exactly what fixed it. I didn't patch licensing or fake a successful sign-in.
- The installer record picked W4Y Ultimate, but the app that runs is Professional for Makers. An uninstall/reinstall came up and its wizard got opened, but it wasn't finished before CAD launched.
- CAD's Software OpenGL option was greyed out before I turned off Enhanced graphics performance. I didn't enable it. The run that worked came after turning off Enhanced graphics and restarting.

## Validation and what's left

Native screenshots show the Professional for Makers window and Part1. After the restart, the app worked and I created a cube and chamfered it. That's the first real modeling success, separate from the earlier native geometry probe.

Before the first SM4L upload, the copied setup checks passed again: launcher, browser profile, browser routing, ZIP refusal checks, matcher/import checks, both offline installer copies, and the header guard's branch and hash checks. The header, event and child-memory probes passed during the investigation under the final conditions described here. I built the CAD MSI helper and verified the payload it installed. There's no need to rerun it just to test the repo.

Still open: save and reopen, and a fresh replication on the desktop. Embedded browser panels still flash. Keep the working CAD graphics setting in place while chasing that.

Native X11 automation was only a research aid and isn't part of the setup. On this KDE/Wayland desktop, asking for 400,400 landed at 500,500, and scaling targets by 1/1.25 fixed it. Don't hard-code that factor on another monitor or machine.

## References

- [UMU launcher](https://github.com/Open-Wine-Components/umu-launcher), [Proton](https://github.com/ValveSoftware/Proton).
- [Microsoft RtlIsNameInExpression contract](https://learn.microsoft.com/en-us/windows/win32/devnotes/rtlisnameinexpression), [ReactOS API test expectations](https://github.com/reactos/reactos/blob/master/modules/rostests/apitests/ntdll/RtlIsNameInExpression.c).
- [Wine Common Controls header implementation](https://github.com/wine-mirror/wine/blob/master/dlls/comctl32/header.c), [Microsoft HDM_LAYOUT](https://learn.microsoft.com/en-us/windows/win32/controls/hdm-layout).
- [WebView2 feature flags](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags), [WebView policies](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-webview-policies), [Chromium SwiftShader](https://github.com/chromium/chromium/blob/main/docs/gpu/swiftshader.md).
- [SOLIDWORKS OpenGL performance settings](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P).

## SpaceMouse view performance (October 7, 2026)

The Linux driver already supported my wired SpaceMouse Pro. A real COM attachment and `ActiveDoc`/`ActiveView` worked under Proton, and every view method passed the native checks. The first socket-to-COM bridge moved the view, but it was slow and jittery, averaging 194 ms per update. Panning with the regular mouse was responsive, so the delay was in my bridge and not in CAD navigation generally.

Moving the calls into my own `ISwAddin` brought frame work down to about 80–100 ms. Most of what was left came from redrawing after each navigation call separately. Turning off view refresh during the grouped calls, restoring it, and doing one redraw got a focused pan/rotation test down to 14–18 ms. The reader now publishes at up to 30 Hz with a short low-pass filter, and stops immediately when you let go. Movement is smooth and the physical tilt goes the right way. Button mapping and large-assembly performance haven't been tested.

The add-in only uses public API calls and registers inside the prefix. I needed HKLM class registration to get the real connection callback. With HKCU only, the load reported success but the callback never came, so that success meant nothing. CAD also kept the old DLL loaded after an unload/reload, so each experimental build got a new class and DLL identity. That let me test new code without restarting CAD and losing an unsaved part. The current v3 identity is in the [SpaceMouse guide](SPACEMOUSE.md).

Input dropped to zero once when the USB connection dropped, and reconnecting fixed it. A timed reader also ran out while I was testing. Continuous navigation now leaves out `--seconds`, and the menu launcher starts the bridge after the host Wine server it depends on. General slowness while sketching and editing models is a separate open issue.

## 2026-10-07 — radio/checkbox labels and an off-screen Save As dialog

Native control inspection found the missing Fillet labels intact. The affected controls use ordinary checkbox/radio styles, not owner drawing. Selecting Full preview changed BM_GETCHECK from 0 to 1, and the viewport showed yellow fillet preview curves. The feature was not accepted by our helper.

SetWindowTheme with empty strings returned 0x8007007B both externally and on CAD's UI thread. Wine's implementation stores names with AddAtomW, which rejects an empty name. Using an unmatched nonempty name, SM4L_NoTheme, succeeded on the UI thread and restored Full preview, Partial preview, No preview, Tangent propagation, Show selection toolbar and Multi Radius Fillet labels in the captured panel. This establishes the workaround for those controls; it does not resolve every missing group header or layout problem.

The launcher now loads a separate UI compatibility add-in from the same bootstrap source. It checks visible checkbox/radio controls every 500 ms, selects the classic painter only when a theme is present, and invalidates them once. It leaves control types, checked state, and model geometry alone. It works without a SpaceMouse or spacenavd.

Save As was visible to Win32 but positioned at x=8600, outside the screen. Moving it over CAD revealed a normal working dialog. Anthony saved examplepart.SLDPRT in the project folder (93,822 bytes); the live CAD title then showed the filename without an unsaved marker. Reopening that file has not been tested. The add-in also recenters owned windows that overlap no monitor, using the owner's monitor work area without resizing them or activating Save. The manual recovery is verified; automatic recovery on another occurrence remains to be observed.

Current UI DLL: C:\sm4l-ui-compat-v2.dll, class {BB75177C-6799-4F57-9B75-10931D6421FA}. The standalone mode is python3 -B spacemouse.py --ui-only. The menu enables it by default; SM4L_UI_COMPAT=0 disables it for future launches. Restart CAD to remove an already loaded UI fix. Registration is scoped to the dedicated prefix. Logs are C:\sm4l-ui-compat.log and the launch's ui-compat.log.

Anthony asked about using the Linux file chooser. KDE kdialog is installed and supports --getsavefilename. A bridge could pass its selected path back into SOLIDWORKS' Save As field while preserving CAD format/options/overwrite handling. That integration is feasible but not implemented yet.

Primary references: [Wine theme implementation](https://github.com/wine-mirror/wine/blob/master/dlls/uxtheme/system.c), [SetWindowTheme](https://learn.microsoft.com/en-us/windows/win32/api/uxtheme/nf-uxtheme-setwindowtheme), and [KDE dialog documentation](https://develop.kde.org/docs/administration/kdialog/).

## 2026-10-07 — modeling performance investigation

Anthony reports delays when changing geometry, such as extruding a sketch. An external redraw took 28–212 ms across samples; full rebuilds roughly 350–719 ms. An in-process probe measured three rebuilds at 436–440 ms, with 320–350 ms of UI-thread CPU time. FeatureStatistics reported Fillet2 40 ms, Sketch1 5 ms, Fillet1 5 ms, Cut-Extrude1 4 ms, Boss-Extrude1 3 ms and Sketch2 2 ms. These describe the current part and session, not an isolated new extrusion or a Windows comparison.

Suppressing EnableFeatureTree made the rebuild call much faster (88–104 ms in the first comparison), but restoring the tree cost another 492–613 ms. That is deferred work, not a verified overall speedup. Direct WM_SETREDRAW batching also failed to improve total time consistently. Classic tree styles and application-wide visual styles did not establish a reliable speedup; application styles were restored. Classic tree styling remains in the live diagnostic session and resets with CAD restart. No permanent performance workaround has been shipped.

A bounded instruction sample during rebuild was dominated by Wine win32u UI/GDI entry points: NtUserMessageCall, NtUserSetWindowPos, NtGdiStretchBlt, NtUserCallNextHookEx, compatible DC/bitmap creation, object deletion, BitBlt and AlphaBlend. Sampling itself perturbs timing and counts syscall entry points; it identifies a UI/GDI lead rather than a precise CPU attribution.

The main thread was scheduled on efficiency cores. Restricting it to CPUs 0–3 changed external rebuild samples from 447/563/414 ms to 399/403/399 ms (about 11% lower median). This did not meet the experiment's 15% threshold, so original affinity was restored. The laptop is already in performance power mode; turbo is enabled. Advanced verification on rebuild is already off. Recent memory pressure was zero, despite almost all swap being allocated; do not infer active swapping solely from swap usage.

CAD's embedded Chromium GPU process used about 49% of one core in a five-second sample. It loaded SwiftShader and also had Intel GPU activity. That is separate from the login WebView2 workaround, and it has not been proven to cause extrusion delays. No browser process was killed or paused.

A reproducible benchmark now runs with python3 -B spacemouse.py --benchmark. It performs one redraw and full rebuild, then reports per-feature timings via the supported API. It does not save, alter dimensions or suppress features; rebuilding can mark a document modified.

Next experiment: compare Wine's client-side and server-side 2D drawing for sldworks.exe only. Wine 10 reads ClientSideGraphics from HKCU\Software\Wine\AppDefaults\sldworks.exe\X11 Driver at startup. That key was absent. Test ClientSideGraphics=N after saving current geometry and restarting CAD; roll back by deleting only that value. The setting has not been applied yet. Keep the existing OpenGL pipeline setting, host server, WebView authentication and SpaceMouse intact.

References: [FeatureStatistics](https://help.solidworks.com/2017/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFeatureManager~FeatureStatistics.html), [EnableFeatureTreeWindow](https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFeatureManager~EnableFeatureTreeWindow.html), [Wine 10 X11 configuration](https://github.com/wine-mirror/wine/blob/wine-10.0/dlls/winex11.drv/x11drv_main.c).

## Off-screen modal recovery correction — 2026-10-07

Saving appeared blocked again. Native inspection found Move Confirmation at x=8600 and Performance Evaluation behind it; the main CAD window was disabled. Moving both over the main window exposed the external-relations confirmation. Anthony then saved and closed CAD normally. No dialog choice or save was performed by the helper.

The automatic recovery repeatedly logged moves while using Wine's reported monitor work area. Centering over the visible owner's rectangle recovered the dialogs. The UI add-in now uses that rectangle instead of the monitor work area, preserving size and activation state. The placement check covers the observed coordinates, a negative-coordinate owner, and an oversized dialog. Live manual recovery and saving are confirmed; the updated automatic path still needs a fresh off-screen dialog event.

The subsequent CAD-only ClientSideGraphics=N experiment produced a completely black startup prompt. Native text inspection recovered the platform-launch warning, but no timing comparison was possible. The value was deleted and the experiment rejected; do not add it to installation defaults. A normal launch without a part argument is being verified after rollback.

## Desktop OOM and launch discipline — 2026-10-07

Anthony reported that systemd-oomd killed KWin at 14:41:41 after RAM and swap filled. His investigation attributed roughly 10 GB RAM and 15 GB swap to Xwayland, with four SOLIDWORKS test instances and their web helpers still running. These crash figures come from his report; the exact allocation leak has not yet been independently profiled. Repeated launch attempts without stopping the old processes contributed to the problem.

Stopped the dedicated prefix with wineserver -k after Anthony confirmed no test instance held unsaved work. A subsequent process check found no sldworks.exe, about 20 GB available RAM and about 4 GB allocated swap. No further CAD launch was attempted. The earlier desktop crash also invalidated the X11 authentication context; Wine reported Invalid MIT-MAGIC-COOKIE-1. Refresh the live desktop environment before future GUI work.

The shared wrapper now checks for an existing sldworks.exe and holds a nonblocking launch lock before starting its server or helpers. This covers our CAD and vendor-launcher commands. The website's independently running Windows service bypasses this shell guard: click Open once and check processes before retrying. Close an existing instance before another launch. The check is deliberately conservative across prefixes. Tests verify both rejection paths occur before server startup. Single-instance control reduces amplification; it does not prove that one instance cannot leak memory.

The next controlled Open started one CAD instance, with current desktop authentication, but no native windows or display driver. Memory stabilized around 11 GB available and Xwayland remained near 38 MB. Stopped the stalled prefix and verified zero CAD before replaying the current vendor request interactively. Anthony saw the launcher and followed its browser prompts. DSLauncherTray was missing from the service-created tray; replacing the tray and backbone with interactive copies using current pipe arguments restored that registration. CAD remained stopped, with about 19 GB RAM available. A new Open request is needed; successful CAD relaunch is not yet verified.

The persistent server inherited file descriptor 9 for the launch lock. Server and background-helper commands now close it, leaving ownership with the launcher. The test verifies no server inheritance. The current server retains the old descriptor until the prefix next stops; do not restart a working CAD session just to clear it.
