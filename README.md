# SM4L: SOLIDWORKS Makers For Linux

Why SM4L? Simple, Fusion has become a husk of what it once was and is mostly just a poorly optimized browser app. And the actual browser app is just a Citrix box (or similar). So, SOLIDWORKS was the next best option, not just because it was cheap ($50 a year) but also because it actually runs on local hardware.

They still require you to have an internet connection, but right now, it's the lesser of two evils. So, getting SOLIDWORKS to run was the easy part, especially with AI helping find all the obscure dependencies I needed to satisfy to get this running under Proton, as close to native as possible.

The biggest challenge was getting the license from the 3DEXPERIENCE portal to pass through. SOLIDWORKS is AGGRESSIVE with hiding the install/open button for the app in 3DEXPERIENCE if you aren't running Windows, and telling your browser to spoof Windows with a user-agent doesn't work. I had to set up a separate Firefox profile that reports Windows everywhere the site checks before the option would show up, and even then, I had to make sure the Windows service it all relies on was able to communicate with the portal.

So, after a few hours... It works. **SOLIDWORKS Design Professional for Makers 2026 SP3.0** runs on one Arch Linux x86_64 laptop through UMU and Proton. On October 7, 2026, I modeled a cube and chamfered it. Getting there took a startup crash fix and turning off Enhanced graphics performance, plus a pile of installer workarounds that are all written up here. I'm going to continue to expand upon this, and get it working on my other machines, but this is at least a template that others can use to improve upon.

## What this is

SM4L is a set of scripts, a small add-in and the written steps to run SOLIDWORKS on Arch Linux, using UMU and a pinned Proton. It isn't an installer. You bring the vendor media and your own license, and the guide walks you through the rest.

## Disclaimer

SM4L is not affiliated with, endorsed by, or supported by Dassault Systèmes, SOLIDWORKS, Microsoft, Valve or Open Wine Components. You need your own SOLIDWORKS license and the vendor media. SM4L contains neither. The repository has no vendor binaries. The patches change only your own Wine prefix and your own installed copy, and they never change the original media.

## Tested on

- Arch Linux x86_64, KDE Plasma on Wayland (KWin).
- An Intel GPU (`Mesa Intel(R) Graphics (MTL)`).
- UMU 1.4.4 with UMU-Proton-10.0-4.
- SOLIDWORKS Design 2026 SP3.0, from the 3DEXPERIENCE SOLIDWORKS platform media.
- A wired 3Dconnexion SpaceMouse Pro, optional.

Nobody has replayed the setup on a second machine yet.

## Quick start

1. Get the vendor media. [DOWNLOAD.md](docs/DOWNLOAD.md) explains the Windows-identifying Firefox profile and how to find the full download. Your account needs the desktop app assigned.
2. Install the host tools and clone this repository, following [INSTALL.md](docs/INSTALL.md), steps 2 and 3.
3. Follow [INSTALL.md](docs/INSTALL.md) from step 4 to step 11. It covers UMU, the prefix, .NET, the platform, CAD, WebView2, the login profile and the launcher service.
4. Finish the fixes in steps 12 to 15: the background units, the header guard, the theme setting and native msxml6.
5. Launch CAD with the menu entry from step 17, then verify with step 18.

`./setup.sh --plan` shows which steps are done and which are left, and changes nothing. `./setup.sh` runs the scriptable steps in order and stops at the manual ones. The script is pending a live test, so follow [INSTALL.md](docs/INSTALL.md) if they disagree.

If something fails, check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) before you try anything else.

## Status

**Verified on the reference machine**

- Installing, signing in through the 3DEXPERIENCE platform, and launching CAD from the browser's Open button and from the menu entry.
- Sketching, extruding, chamfering and rotating a model.
- SpaceMouse navigation, with the view following the cap.
- Checkbox and radio labels in the PropertyManager, with the theme off.
- PropertyManager section headers, including through drag and resize.
- Save As 3MF, verified once. The file imported into PrusaSlicer.

**Pending confirmation**

- The status-bar `SetWindowPos` dedupe is on by default. It was measured in an A/B run, but not yet after a restart in normal mode.
- The leftover-process cleanup is enabled. It hasn't yet acted on a real CAD exit.
- The theme setting is re-applied before each start by `setup/ensure_theme_off.py`. That isn't confirmed in a real start yet.
- Saving a `.SLDPRT` and reopening it.

## Known issues

| Issue | Status | Workaround |
| --- | --- | --- |
| Embedded browser panels flash | Open | None yet. CAD still works while the panels flash |
| Model rebuilds are slow | Open | In measured runs, most of the time goes to Wine window-system calls |
| The cause of the header drift isn't identified | Open | The header hook in the UI add-in keeps the headers visible |
| CAD has hung on exit once | Open | The cleanup in `addin/cad_cleanup.py` handles the stuck process. See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Save As 3MF needs native msxml6 | Verified once | Step 15 in [INSTALL.md](docs/INSTALL.md) |
| Labels need the theme off | Verified | Step 14. The look is classic and flatter |
| Native KDE file chooser isn't integrated | Open | Use the normal file dialogs |
| Fresh-machine replay not done | Open | Check each step's result as you go |

## Where to start

1. [Download the installer from Linux](docs/DOWNLOAD.md).
2. [Install SOLIDWORKS on Arch Linux](docs/INSTALL.md). This is the full path, in order.
3. [Troubleshoot](docs/TROUBLESHOOTING.md) when a step fails.
4. [Set up the SpaceMouse](docs/SPACEMOUSE.md), if you have one.
5. [Read the findings](docs/FINDINGS.md) for why each fix exists.

Moving from the earlier layout? See [MIGRATION.md](docs/MIGRATION.md).

## What you need to bring

The repository has the compatibility code and its own `swcompat.dll` proxy. Everything else comes from the original source: the SOLIDWORKS media, the Microsoft prerequisites and Proton. You need your own account and its assigned license.

The repository leaves out vendor payloads, installed prefixes, cookies, launch tickets and crash dumps on purpose.

## Layout

| Path | What it holds |
| --- | --- |
| `bin/` | Scripts you run every day: launch, the launcher service, the menu entry, the login profile, the unit installer |
| `setup/` | One-time install and patch steps, the DLL proxy and its source |
| `addin/` | The SpaceMouse and UI add-in source, the bridge, the dedupe rules and the leftover-process cleanup |
| `units/` | systemd user unit templates |
| `tests/` | Assert-based checks for the scripts above |
| `experiments/` | Unverified or diagnostic tools, and native probes. Don't run these as part of the install |
| `docs/` | The guides, the findings record and `tested-versions.json` |

Run the checks in [INSTALL.md](docs/INSTALL.md) before patching anything. Every patch checks the file's hash first. If one refuses, you have a different build, so stop and look at it. Don't remove the guard.

## License

SM4L is free software under the [GNU General Public License v3.0](LICENSE). Copyright 2026 Anthony Dragone.

The license covers the scripts, the add-in source and the documentation in this repository. It doesn't cover SOLIDWORKS, the 3DEXPERIENCE platform, Microsoft components, Proton, UMU or any other vendor software. You need your own licenses and media for those.
