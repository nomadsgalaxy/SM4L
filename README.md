# SM4L: SOLIDWORKS Makers For Linux

Why SM4L? Simple, Fusion has become a husk of what it once was and is mostly just a poorly optimized browser app. And the actual browser app is just a Citrix box (or similar). So, SOLIDWORKS was the next best option, not just because it was cheap ($50 a year) but also because it actually runs on local hardware.

They still require you to have an internet connection, but right now, it's the lesser of two evils. So, getting SOLIDWORKS to run was the easy part, especially with AI helping find all the obscure dependencies I needed to satisfy to get this running under Proton, as close to native as possible.

The biggest challenge was getting the license from the 3DEXPERIENCE portal to pass through. SOLIDWORKS is AGGRESSIVE with hiding the install/open button for the app in 3DEXPERIENCE if you aren't running Windows, and telling your browser to spoof Windows with a user-agent doesn't work. I had to set up a separate Firefox profile that reports Windows everywhere the site checks before the option would show up, and even then, I had to make sure the Windows service it all relies on was able to communicate with the portal.

So, after a few hours... It works. **SOLIDWORKS Design Professional for Makers 2026 SP3.0** runs on my Arch Linux x86_64 laptop through UMU and Proton. On October 7, 2026, I modeled a cube and chamfered it. Getting there took a startup crash fix and turning off Enhanced graphics performance, plus a pile of installer workarounds that are all written up here. I'm going to continue to expand upon this, and get it working on my other machines, but this is at least a template that others can use to improve upon.

## Known Issues

Before you dive into this, please note that this is still in "proof of concept" stage, I just got this working, and haven't tested it with anything more complex than a cube with some chamfers. There's a lot of broken UI that I'm working on fixing.

## Where to start

1. [Download the installer from Linux](docs/DOWNLOAD.md). The 3DEXPERIENCE site hides the desktop app from Linux browsers, so this covers the Firefox setup that gets around that.
2. [Follow the replication guide](docs/REPLICATE.md). It's the exact route I used, with the commands, source hashes, registry settings and rollback steps.
3. [Read the findings](docs/FINDINGS.md) if you want to know why each fix exists and which experiments I dropped.
4. [Set up the SpaceMouse](docs/SPACEMOUSE.md) if you have one.

[checkpoint.json](checkpoint.json) records the versions I tested and the evidence behind them.

## Where it stands

This is a working laptop setup with a written guide. It isn't an unattended installer, and nobody has replayed it on a fresh machine yet. That's the next test, on my desktop.

- **Works:** installing, signing in, launching CAD, and modeling a chamfered cube.
- **Works:** SpaceMouse camera movement is smooth and tilts the right way. [Install the menu launcher](docs/REPLICATE.md#11-install-the-start-menu-item) and it starts automatically.
- **Not tested yet:** saving a part and reopening it.
- **Still broken:** embedded browser panels flash.

One thing to be upfront about: the installer record says I picked W4Y Ultimate, but the running CAD window says Professional for Makers. I didn't uninstall and reinstall in between the license error and the launch that worked. The mismatch was a guess I had at one point, not a known cause, and it's not a reason to mess with licensing.

## What you need to bring

The repo has my compatibility code and my own `swcompat.dll` proxy. Everything else comes from the original source: the SOLIDWORKS media, the Microsoft prerequisites and Proton. You need your own Makers account and its assigned license.

I left out vendor payloads, installed prefixes, cookies, launch tickets and crash dumps on purpose.

## What's in here

| Files | What they do |
| --- | --- |
| `launch_solidworks.sh`, `install_desktop.py` | Adds a SOLIDWORKS entry to your app menu |
| `spacemouse.py`, `spacemouse-view.c` | Connects a Linux SpaceMouse to the focused SOLIDWORKS view |
| `launch_proton.sh` | Runs everything in a dedicated prefix with fsync/esync off, a host Wine server and a bigger file-descriptor budget |
| `patch_offline_installer.py` | Makes a checked copy of the installer that skips a false IE10 prerequisite check |
| `rtl_name_match.c`, `swcompat.dll`, directory-compat scripts | Supplies the Unicode/DOS wildcard matcher the vendor dictionary compiler expects |
| `prepare_design_install.py`, `cad-msi-experiment.c` | Extracts Spatial InterOp properly and runs the exact CAD MSI install I used |
| Firefox scripts | A separate Firefox profile that identifies as Windows, plus routing for login links from the prefix |
| `patch_header_layout.py` | A version-pinned, prefix-only guard for the null `HDM_LAYOUT` crash |
| `*_probe.c`, `test_*.py` | Reproductions and checks for each failure and patch |

Run the checks at the end of the replication guide before patching anything. Every patch checks the file's hash first. If one refuses, you've got a different build, so stop and look at it. Don't remove the guard.
