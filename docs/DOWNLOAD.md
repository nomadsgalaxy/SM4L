# Download the same installer from Linux

The 3DEXPERIENCE site hid desktop SOLIDWORKS options when it detected Linux. Selecting a Chrome–Windows label in the site did not reliably reveal the desktop app. Our working browser setup used a dedicated Firefox profile whose actual HTTP User-Agent **and** JavaScript platform/OS identity reported Windows.

You can prepare this profile and download the full media before installing Proton or starting the Windows launcher service. The service matters later for the browser's installed-app Open action.

## 1. Open your own Makers platform with the Windows Firefox profile

Clone this repository and install Firefox and Python if needed:

```bash
git clone https://github.com/nomadsgalaxy/SM4L.git
cd SM4L
sudo pacman -S --needed firefox python
```

Find your **own 3DEXPERIENCE platform URL** from your Makers welcome email, account links, or the dashboard you already use. Use that exact HTTPS `*.3ds.com` URL, including its dashboard fragment if provided. Do not use another customer's tenant address or guess the region.

Run this from a terminal in your graphical Linux session. Replace the placeholder URL:

```bash
export SOLIDWORKS_PROTON_STATE="$HOME/.local/share/solidworks-proton"
export SOLIDWORKS_PLATFORM_URL='https://YOUR-PLATFORM-HOST.3dexperience.3ds.com/'
python3 -B launch_windows_browser.py
```

This opens a separate Firefox instance/profile at:

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

A short-lived local page checks both the request header and `navigator.userAgent`, `navigator.platform` and `navigator.oscpu`, then sends that window to your platform. The terminal should print **Verified Windows identity**. The helper stays running while Firefox is open; that is expected.

Sign in normally in this new Firefox window. It has separate cookies from your normal Linux browser. Use it for the remaining download steps. The normal browser default and existing Firefox profiles are unchanged.

On the laptop, Firefox 157.0 passed the identity check, and Anthony confirmed that SOLIDWORKS Design appeared in the authenticated dashboard. Other Firefox versions need the same check; do not assume the override worked if the helper reports a mismatch.

## 2. Use the full-media download route

This was the vendor route used to obtain the laptop installer:

1. Open **Compass** in the authenticated platform.
2. Go to **All Apps**.
3. Open **Members Control Center**.
4. Choose **Configure Apps Installation**, the gear tab.
5. Select **3DEXPERIENCE SOLIDWORKS Desktop**.
6. Select **Full**, then **Download**.

The full download was listed at about **26.6 GB** and saved as:

```text
SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip
```

That is the **R2026x HotFix 4.13 Windows64 platform/desktop full media** used in this repository. It is different from the later **SOLIDWORKS Design 2026 SP3.0** payload downloaded by the Windows Installation Manager.

The initial Welcome/app list did not show the desktop app consistently. Use the Members Control Center installation/download view rather than treating an empty Welcome list as proof that the download is unavailable.

If Dassault offers only a different release, record its filename. The patches here pin the exact original files and will refuse another build. We do not host or reconstruct the vendor ZIP, and changing a filename does not make a new release compatible.

## 3. Confirm the download and extract it

Wait for the browser download to finish completely. The laptop ZIP had 649 entries and expanded to 28,567,505,049 bytes. The later CAD download and installed application need additional space.

From the SM4L checkout:

```bash
mkdir -p "$SOLIDWORKS_PROTON_STATE/media"
unzip "$HOME/Downloads/SOLIDWORKS_3DEXP_Desktop.Full-CP0490V6R2026x.HF4.13.Windows64.zip" \
  -d "$SOLIDWORKS_PROTON_STATE/media"
export MEDIA_1="$SOLIDWORKS_PROTON_STATE/media/SOLIDWORKS_3DEXP_Desktop.Full.Windows64/1"
python3 -B test_patch_offline_installer.py "$MEDIA_1"
```

Use your actual download location if Firefox saved elsewhere. `MEDIA_1` must contain the original `setup.exe`, `setup_noUAC.exe` and `media.db`; inspect the extracted folder if the vendor's layout differs.

The supported original `setup.exe` SHA256 is:

```text
c3aeeecdb030e124c74eb9a4897ff08c60122e2ed7bc2058b313c8c4cddb222a
```

The check verifies the original installer copies and exact one-byte patch location. It is not a checksum of the entire ZIP. Keep the original media unchanged; [the replication guide](REPLICATE.md) creates a separately named patched setup copy later.

## If the Linux block remains

- Make sure the platform is open in the **dedicated Windows-identifying Firefox window**, not Vivaldi or another normal Linux browser. The window looks like ordinary Firefox; the verified profile is what matters.
- If you get **Identity mismatch**, close this dedicated Firefox instance and rerun the helper. Do not proceed based only on a site dropdown saying Chrome–Windows.
- If it times out, check the terminal message and the private `browser-windows-firefox.log` under the state directory. The local check must load before the redirect can happen. Keep logs and profile cookies outside Git.
- If the profile is already open, use that existing window. Close it before rerunning the setup helper so the new instance can own the profile.
- If you see **Install/Open** later, that belongs to the Windows launcher handoff. A spinning Open button is a separate service/authentication problem; it does not mean the ZIP download is corrupt.
- If the expected full-media controls still do not appear after verified Windows identity and normal sign-in, confirm the assigned Makers role and platform URL. Do not bypass authentication or licensing.

After extraction, continue with [Replicate the working laptop setup](REPLICATE.md). Leave the authenticated dedicated profile available for the CAD login flow, or close it normally and reuse it later; closing Firefox does not delete the profile.
