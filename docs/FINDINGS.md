# What it took to get the laptop working

These are the fixes from October 6–7, 2026 that held. The commands and final settings are collected in [REPLICATE.md](REPLICATE.md). Before this, I spent some time on native geometry experiments, but none of that was used to actually run SOLIDWORKS, so it's not in SM4L.

## Fixes that stuck

| What broke | What I found | What I kept |
| --- | --- | --- |
| Installer demands IE10 even with IE11 registry values | The bootstrap looks up a missing WinINet `HttpWebSocketReceive` export | A one-byte branch change in a separate copy of the offline setup, checked against the whole file's hash |
| Login Manager registration fails | The real Framework64 RegAsm was missing after the media's .NET 4.8.1 DISM attempt | Real Microsoft .NET 4.8 through Proton's Winetricks. Vendor registration then returns zero |
| Object Modeler dictionary compilation fails | CATSysTS looks up an NTDLL `RtlIsNameInExpression` that isn't there, and the compiler returns one | My proxy implements real Unicode/DOS wildcard matching. The compiler and the vendor install both return zero |
| CAD MSI can't unzip Spatial InterOp | ZIP-shell `SHCreateItemFromParsingName` fails with `0x8000ffff` | Extract the real ZIP with CRC/size checks and turn off only that redundant action in a separate MSI copy |
| MSI succeeds but there's no CAD core | The first optional-feature list left the core out | The direct MSI install uses `ADDLOCAL=ALL`, which installed the actual CAD executable |
| Platform-launched CAD never shows a window | The service's backbone and the CAD it starts load no `winex11`. Wine runs non-interactive services on `__wineservice_winstation\\Default` | Set the `3DEXPERIENCELauncher` service `Type` to `0x110`. The backbone and CAD then load `winex11` and show the splash and main window |
| Linux browser hides the desktop app | A Windows label or user-agent on its own didn't bring the app back | Dedicated Firefox profile with a Windows user-agent plus Win32/Windows navigator overrides, verified live |
| CAD login opens the default Linux browser | WineBrowser sends links to the system browser | A prefix-only handler opens the dedicated Firefox profile on the host |
| WebView2 prerequisite error | The vendor loader exists, but the runtime and its registration don't | Installed Microsoft's real x64 Evergreen standalone runtime |
| WebView startup breakpoint | A restricted event handle has EVENT_MODIFY_STATE, but the fsync lookup also needs SYNCHRONIZE | Keep fsync/esync off. The event probe signals and sees the event |
| WebView GPU process launch error 39 | Native child-memory write returns 299, because the server's process_vm_writev returns EPERM across user namespaces | Start this prefix's persistent Wine server on the host before UMU. The allocate/write/read roundtrip then passes through UMU |
| Host server runs out of descriptors | The server inherited a limit of 2048 and hit it | Raise the soft limit to the existing hard limit before starting the server. The laptop's budget is 2097152 |
| Embedded login stays blank | DXVK divide-by-zero, and builtin D3D11/WARP has no usable renderer | Builtin D3D overrides for WebView only, plus HKLM SwiftShader arguments. The real login and error pages render |
| CAD crashes during UI startup | Two native CAD minidumps: access violation at COMCTL32+0x2ac1e reading address 8, a null HDLAYOUT | A prefix-local, version-pinned guard returns FALSE on null. The valid-layout probe still passes. The native,builtin override applies to CAD only |
| CAD opens with a black viewport | Menus, options and the feature tree render. Intel Mesa renderer, Enhanced graphics on | Turn off Enhanced graphics performance, apply and restart. After that I modeled a cube and chamfered it |
| Checkbox and radio labels missing in the PropertyManager | Wine's themed checkboxes and radio buttons draw without a text colour, so SOLIDWORKS' label colour is lost | Set `HKCU\Software\Microsoft\Windows\CurrentVersion\ThemeManager` `ThemeActive` to `0` in the prefix, so SOLIDWORKS uses classic controls. Labels render with no add-in. The classic look is accepted |

During the investigation, the directory matcher passed 191 expectation cases pulled independently from ReactOS's API tests. The repo's own check also covers DOS wildcards, Unicode, custom uppercase tables, import preservation, backup preservation, and refusing unsupported builds.

## Browser-to-launcher handoff

**Update, October 7:** the real fix for the headless backbone is the service type. Wine puts every service that isn't flagged `SERVICE_INTERACTIVE_PROCESS` on a hidden desktop, and children inherit it. Setting the service `Type` from `0x10` to `0x110` and restarting the prefix put the backbone and CAD on the visible desktop on the first try. The manual recovery below is kept as a record. You shouldn't need it anymore.

The website's Install/Open buttons depend on a lot at once: the real Windows launcher service, the installed apps, sign-in, browser identity, and the trusted-platform confirmation. Seeing those buttons doesn't prove CAD is licensed or visible.

The service is `3DEXPERIENCELauncher`, listening at `http://127.0.0.1:20250/`. At first it accepted TCP but hung on HTTP. Stopping and restarting it with the desktop environment available got HTTP 200 back. The tray also started with no X11 driver, so the backbone couldn't find the Windows `DSLauncherTray` window. Restarting the real tray interactively made the backbone's `postStatus` succeed, and SWXDesktopLauncher started.

After a reboot, the service's backbone could still come up headless. My manual recovery left the service alone and started the same vendor backbone interactively with its current named-pipe arguments:

1. Find the backbone that belongs to this prefix's service by its mapped executable, and confirm it has no winex11 mapping. Don't pick a backbone from another prefix or one that's already interactive.
2. Read that live process's NUL-separated `/proc/<pid>/cmdline` in memory. The argv I saw had three entries: the vendor executable and two pipe arguments. Don't print or save them.
3. Start the installed `3DEXPERIENCELauncherBackbone.exe` through the same Proton prefix and desktop environment, with those original argv entries after the executable, unchanged.
4. Keep the service and the interactive tray running, click Open once, and accept the normal vendor trust prompt. A restarted service gets a new pipe, so never reuse an old one.

Some fresh signed-in launches also needed an interactive replay. For the ENOPLMCSAClient child I saw, Wine had rewritten the argv: argv[0] was empty, argv[1] was `SWXDesktopLauncher`, the original launcher arguments sat in argv[2:16], argv[3] was `-Prfctx`, and argv[12] was `-RegistryUrl`. I kept those 14 original arguments in memory and started the platform's real SWXDesktopLauncher through my interactive launcher, leaving out the extra ENO arguments tacked on the end. That's what this one command layout looked like. It's not a general parser for other releases.

Those arguments carry private account and platform context plus launch tickets, so none of them are saved in SM4L. Replaying the laptop's arguments on the desktop would be wrong. If the same headless failure shows up there, capture a fresh request on that machine. This recovery still needs a proper, tested implementation. Once sign-in and the runtime fixes were in place, launching `sldworks.exe` directly worked.

## References

- [UMU launcher](https://github.com/Open-Wine-Components/umu-launcher), [Proton](https://github.com/ValveSoftware/Proton).
- [Microsoft RtlIsNameInExpression contract](https://learn.microsoft.com/en-us/windows/win32/devnotes/rtlisnameinexpression), [ReactOS API test expectations](https://github.com/reactos/reactos/blob/master/modules/rostests/apitests/ntdll/RtlIsNameInExpression.c).
- [Wine Common Controls header implementation](https://github.com/wine-mirror/wine/blob/master/dlls/comctl32/header.c), [Microsoft HDM_LAYOUT](https://learn.microsoft.com/en-us/windows/win32/controls/hdm-layout).
- [WebView2 feature flags](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags), [WebView policies](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-webview-policies), [Chromium SwiftShader](https://github.com/chromium/chromium/blob/main/docs/gpu/swiftshader.md).
- [SOLIDWORKS OpenGL performance settings](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P).

