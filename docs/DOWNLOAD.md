# Download the installer from Linux

The 3DEXPERIENCE site hides the desktop SOLIDWORKS options when it sees a Linux browser. Picking a Chrome–Windows label in the site didn't reliably bring the app back. What worked was a dedicated Firefox profile where both the HTTP User-Agent **and** the JavaScript platform/OS fields say Windows.

You can do this before installing Proton or starting the Windows launcher service. The launcher service only matters later, for the browser's Open button.

## 1. Open your Makers platform in the Windows Firefox profile

Clone the repo and install Firefox and Python if you don't have them:

```bash
git clone https://github.com/nomadsgalaxy/SM4L.git
cd SM4L
sudo pacman -S --needed firefox python
```

You need **your own 3DEXPERIENCE platform URL**. It's in your Makers welcome email, your account links, or the dashboard you already use. Use that exact HTTPS `*.3ds.com` address, including the dashboard fragment if it has one. Don't use someone else's tenant address and don't guess the region.

Run this from a terminal inside your graphical session, with your URL in place of the placeholder:

```bash
export SOLIDWORKS_PROTON_STATE="$HOME/.local/share/solidworks-proton"
export SOLIDWORKS_PLATFORM_URL='https://YOUR-PLATFORM-HOST.3dexperience.3ds.com/'
python3 -B launch_windows_browser.py
```

That opens a separate Firefox instance with its own profile at:

```text
~/.local/share/solidworks-proton/browser-windows-firefox
```

The script sets these built-in Firefox overrides:

| Preference | Value |
| --- | --- |
| `general.useragent.override` | Windows Firefox User-Agent using your installed Firefox version |
| `general.platform.override` | `Win32` |
| `general.oscpu.override` | `Windows NT 10.0; Win64; x64` |
| `general.appversion.override` | `5.0 (Windows)` |

Before it sends you to the platform, a short-lived local page checks the request header plus `navigator.userAgent`, `navigator.platform` and `navigator.oscpu`. The terminal should print **Verified Windows identity**. The helper keeps running while Firefox is open. That's expected.

Sign in normally in the new window. It has its own cookies, separate from your usual Linux browser, so use it for the rest of the download. Your default browser and any existing Firefox profiles stay as they were.

On my laptop, Firefox 157.0 passed the identity check and SOLIDWORKS Design showed up in the signed-in dashboard. If you're on a different Firefox version, the same check still has to pass. If the helper reports a mismatch, the override didn't take.

## 2. Get the full media

This is the route I used to get the installer:

1. Open **Compass** on the signed-in platform.
2. Go to **All Apps**.
3. Open **Members Control Center**.
4. Choose **Configure Apps Installation** (the gear tab).
5. Select **3DEXPERIENCE SOLIDWORKS Desktop**.
6. Select **Full**, then **Download**.

The full download was listed at about **26.6 GB** and saved as:

```text
SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip
```

That's the **R2026x HotFix 4.13 Windows64 platform/desktop full media** this repo is built around. It's not the same thing as the **SOLIDWORKS Design 2026 SP3.0** payload that the Windows Installation Manager downloads later.

The Welcome page's app list didn't show the desktop app consistently for me. Go through the Members Control Center instead of taking an empty Welcome list to mean the download isn't there.

If Dassault only offers you a different release, write down its filename. The patches here are pinned to the exact original files and will refuse anything else. I don't host or rebuild the vendor ZIP, and renaming a file won't make a different release compatible.

## 3. Check the download and extract it

Let the download finish completely. My ZIP had 649 entries and unpacked to 28,567,505,049 bytes. The CAD download and the installed app need more space on top of that.

From the SM4L checkout:

```bash
mkdir -p "$SOLIDWORKS_PROTON_STATE/media"
unzip "$HOME/Downloads/SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip" \
  -d "$SOLIDWORKS_PROTON_STATE/media"
export MEDIA_1="$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1"
python3 -B test_patch_offline_installer.py "$MEDIA_1"
```

Change the path if Firefox saved the ZIP somewhere else. `MEDIA_1` has to point at the folder with the original `setup.exe`, `setup_noUAC.exe` and `media.db`. If the vendor's layout looks different, check the extracted folder.

The supported original `setup.exe` SHA256 is:

```text
c3aeeecdb030e124c74eb9a4897ff08c60122e2ed7bc2058b313c8c4cddb222a
```

The check confirms the original installer files and the exact byte the patch will change. It isn't a checksum of the whole ZIP. Leave the original media alone. [The replication guide](REPLICATE.md) makes a separately named patched copy later.

## If the site still hides the app

- Make sure you're in the **dedicated Windows-identifying Firefox window**, not Vivaldi or your normal browser. It looks like regular Firefox. The profile is what matters.
- If you get **Identity mismatch**, close that Firefox instance and run the helper again. Don't carry on just because a dropdown on the site says Chrome–Windows.
- If it times out, read the terminal message and the private `browser-windows-firefox.log` in the state directory. The local check page has to load before the redirect happens. Keep logs and profile cookies out of Git.
- If the profile is already open, use that window. Close it before rerunning the helper so the new instance can take over the profile.
- If you see **Install/Open** later, that's the Windows launcher handoff. A spinning Open button is a service or sign-in problem. It doesn't mean your ZIP is corrupt.
- If the full-media controls still don't appear after a verified Windows identity and a normal sign-in, check that your Makers role is assigned and that the platform URL is right. Don't try to get around sign-in or licensing.

Once it's extracted, carry on with [the replication guide](REPLICATE.md). You can leave the signed-in profile open for the CAD login later, or close it and come back to it. Closing Firefox doesn't delete the profile.
