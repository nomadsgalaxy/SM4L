# What made the laptop work

This record describes the experiments completed on October 6–7, 2026. The commands and final settings are collected in [REPLICATE.md](REPLICATE.md). Native geometry experiments preceded this work but were not used to run the desktop; they are excluded from SM4L.

## Verified fixes

| Failure | Evidence | Change retained in the working setup |
| --- | --- | --- |
| Installer demands IE10 despite IE11 registry values | The bootstrap looks up missing WinINet `HttpWebSocketReceive` | Whole-file-hash-checked, one-byte branch change in a separate offline setup copy |
| Login Manager registration fails | Real Framework64 RegAsm missing after the media's .NET 4.8.1 DISM attempt | Proton Winetricks installs real Microsoft .NET 4.8; vendor registration returns zero |
| Object Modeler dictionary compilation fails | CATSysTS looks up absent NTDLL `RtlIsNameInExpression`; compiler returns one | Our proxy implements real Unicode/DOS wildcard matching; compiler and vendor installation return zero |
| CAD MSI cannot unzip Spatial InterOp | ZIP-shell `SHCreateItemFromParsingName` fails with `0x8000ffff` | Extract real ZIP with CRC/size checks; disable only that redundant action in a separate MSI copy |
| MSI succeeds but no CAD core exists | Initial optional-feature list omitted the core | Exact direct MSI experiment uses `ADDLOCAL=ALL`; actual CAD executable installed |
| Linux browser hides the desktop app | Selecting a Windows label/user-agent alone did not provide the app | Dedicated Firefox Windows user-agent plus Win32/Windows navigator overrides; live header and navigator check |
| CAD login opens default Linux browser | WineBrowser routes links to the system browser | Prefix-only handler opens the dedicated Firefox profile on the host |
| WebView2 prerequisite error | Vendor loader exists, runtime and registration absent | Real Microsoft x64 Evergreen standalone runtime installed |
| WebView startup breakpoint | Restricted event handle has EVENT_MODIFY_STATE; fsync lookup also requires SYNCHRONIZE | Keep fsync/esync off; actual event probe signals and observes the event |
| WebView GPU process launch error 39 | Native child-memory write returns 299; server's process_vm_writev returns EPERM across user namespaces | Start this prefix's persistent Wine server on the host before UMU; allocation/write/read roundtrip passes through UMU |
| Host server exhausts descriptors | Server inherited limit 2048 and reached it | Raise soft limit to existing hard limit before starting server; laptop budget 2097152 |
| Embedded login stays blank | DXVK divide-by-zero; builtin D3D11/WARP has no usable renderer | WebView-only builtin D3D overrides plus HKLM SwiftShader arguments; real login/error HTML renders |
| CAD crashes during UI startup | Two native CAD minidumps: access violation at COMCTL32+0x2ac1e, reading address 8, null HDLAYOUT | Prefix-local version-pinned guard returns FALSE for null; valid layout probe still succeeds; CAD-only native,builtin override |
| CAD window opens with black viewport | Menus/options/feature tree render; Intel Mesa renderer detected; Enhanced graphics enabled | Clear Enhanced graphics performance, apply and restart; Anthony models a cube and chamfer |

The directory matcher passed 191 independently extracted ReactOS API expectation cases during the investigation. The repository check also covers DOS wildcard cases, Unicode, custom uppercase tables, import preservation, backup preservation and unsupported-build refusal.

## Browser-to-launcher handoff

The website's Install/Open controls depend on the real Windows launcher service, the installed applications, authentication, browser identity and trusted-platform confirmation. They are not proof that CAD is licensed or visible.

The service was named `3DEXPERIENCELauncher`. Its endpoint is `http://127.0.0.1:20250/`. Initially it accepted TCP but hung on HTTP; stopping and starting that service with the desktop environment restored HTTP 200. The tray initially had no X11 driver, and the backbone could not find the Windows `DSLauncherTray` window. Restarting the real tray interactively made backbone `postStatus` succeed and allowed SWXDesktopLauncher to start.

After a reboot, the service's backbone could still be headless. Our manual recovery preserved the service and launched the same vendor backbone interactively with its current original named-pipe arguments. The exact procedure was:

1. Identify the prefix-owned service backbone from its actual mapped executable; confirm it has no winex11 mapping. Do not select an unrelated prefix or an already interactive backbone.
2. Read that live process's NUL-separated `/proc/<pid>/cmdline` in memory. The observed original argv had three entries: the vendor executable and two pipe arguments. Do not print or save them.
3. Start the installed `3DEXPERIENCELauncherBackbone.exe` through the same Proton/prefix and desktop environment with the original argv entries after the executable, unchanged.
4. Keep the service and interactive tray running, click Open once, and resolve the ordinary vendor trust prompt. A restarted service has a new pipe; do not reuse an old captured one.

Some fresh authenticated launches likewise needed an interactive replay. For the observed ENOPLMCSAClient child, Wine rewrote the argv: argv[0] was empty, argv[1] was `SWXDesktopLauncher`, the original launcher arguments occupied argv[2:16], argv[3] was `-Prfctx`, and argv[12] was `-RegistryUrl`. We retained those 14 original arguments in memory and started the actual platform SWXDesktopLauncher through our interactive launcher. Extra appended ENO arguments were excluded. This is evidence for that specific observed command layout, not a generic parser for another release.

Those argv values include private account/platform context and launch tickets. They were not saved in SM4L. Replaying laptop arguments on the desktop would be incorrect; capture only a fresh desktop request if the same headless failure recurs. This recovery still needs a portable, tested implementation. Direct `sldworks.exe` launch worked after the authentication and runtime fixes.

## Experiments we dropped or did not prove

- Changing IE registry numbers did not supply the missing WinINet export.
- `setup_noUAC.exe` hit the vendor elevation requirement; the normal administrator setup copy was used.
- The media's .NET 4.8.1 DISM result did not supply RegAsm. We do not claim full .NET 4.8.1 support.
- A WebView Windows 11 app override did not fix startup; the original Proton win7 override was restored.
- A fresh WebView user-data-folder policy did not fix the blank panel; that override was removed.
- A local headless DOM smoke test was inconclusive. Native rendered login/error pages were the real rendering evidence.
- Tenant casing was not established as the cause of the server-access error. No casing patch was applied.
- License error 1002 appeared, but its exact resolution is unknown. We did not patch licensing or authenticate with invented success.
- The installer record selected W4Y Ultimate, while the running app is Professional for Makers. An uninstall/reinstall was proposed and its wizard opened, but none was completed before CAD launched.
- CAD Software OpenGL was greyed out before disabling Enhanced graphics performance. We did not enable it; the final successful report followed disabling Enhanced graphics and restarting.

## Validation and remaining work

Native screenshots confirmed the Professional for Makers window and Part1. Anthony reported that the restarted application worked and that he created a cube and chamfered it. This is the first real desktop modeling success, separate from the earlier native geometry probe.

The copied setup checks passed again before the first SM4L upload: launcher, browser profile, browser routing, ZIP refusal checks, matcher/import checks, both offline installer copies, and header-guard branch/hash checks. The header, event and child-memory native probes passed during the investigation under their documented final conditions. The CAD MSI helper was built and its successful installed payload was verified; do not rerun it merely to test the repository.

Save/reopen, SpaceMouse and fresh desktop replication remain unverified. Embedded browser elements still flash. These are the next tests; the successful CAD graphics setting should stay in place while investigating browser rendering.

Native X11 automation was only a research aid and is excluded from the setup. On this KDE/Wayland desktop, requested coordinates 400,400 produced actual 500,500; scaling the target by 1/1.25 corrected interaction. Do not hard-code that laptop factor on another monitor or machine.

## Primary references

- [UMU launcher](https://github.com/Open-Wine-Components/umu-launcher), [Proton](https://github.com/ValveSoftware/Proton).
- [Microsoft RtlIsNameInExpression contract](https://learn.microsoft.com/en-us/windows/win32/devnotes/rtlisnameinexpression), [ReactOS API test expectations](https://github.com/reactos/reactos/blob/master/modules/rostests/apitests/ntdll/RtlIsNameInExpression.c).
- [Wine Common Controls header implementation](https://github.com/wine-mirror/wine/blob/master/dlls/comctl32/header.c), [Microsoft HDM_LAYOUT](https://learn.microsoft.com/en-us/windows/win32/controls/hdm-layout).
- [WebView2 feature flags](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags), [WebView policies](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-webview-policies), [Chromium SwiftShader](https://github.com/chromium/chromium/blob/main/docs/gpu/swiftshader.md).
- [SOLIDWORKS OpenGL performance settings](https://help.solidworks.com/2026/english/SolidWorks/sldworks/c_Performance_Settings_with_OpenGL.htm?format=P).
