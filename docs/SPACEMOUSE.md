# SpaceMouse on Linux

My wired **3Dconnexion SpaceMouse Pro** (`046d:c62b`) now drives the SOLIDWORKS view through the regular Linux `spacenavd` daemon. I tested it on real geometry and the camera moves. The first version was too slow, and bumping the sensitivity helped. The original remote-COM path averaged 194 ms per update and felt jittery. Moving it into an in-process add-in with batched redraws got the same pan/rotation test down to 14–18 ms. Now it's smooth and the cap tilts the right way.

It uses SOLIDWORKS' public view API for pan, zoom, pitch, yaw and roll. You don't need the Windows USB driver or the Windows 3DxSolidWorks add-in. The API check returned success for all five operations and confirmed the zoom actually changed by reading back `Scale2` before restoring it. Buttons aren't mapped yet.

## Set up the driver

On Arch, install the driver and client library if you don't have them:

```bash
sudo pacman -S --needed spacenavd libspnav clang lld wine
sudo systemctl enable --now spacenavd
```

`spacenavd` owns the device, and my reader talks to its Unix socket, so your account doesn't need direct access to every input device. On the reference machine the daemon's X11 connection failed, but the Unix socket worked fine, so I didn't bother fixing its X11 auth.

From the SM4L checkout, with the same prefix and Proton environment as the replication guide:

```bash
python3 -B addin/spacemouse.py --listen --seconds 10
```

Move the cap while this runs. It should find the SpaceMouse and print six-axis packets. `--listen` also prints button numbers, which will help when buttons get mapped. If the daemon logs `No such device` and drops it, check the USB cable and plug it back in. That happened to me once, and reconnecting fixed it.

## Run it

With SOLIDWORKS running, open a part and keep its window focused:

```bash
python3 -B addin/spacemouse.py
```

The helper compiles `spacemouse-view.c` into a loader and my own native COM add-in, using the installed clang/lld and Wine import libraries. It registers the add-in inside the dedicated Wine prefix only, then loads it through SOLIDWORKS' `LoadAddIn` API. A timer on CAD's UI thread reads the newest packet and moves the active document's view. Input is ignored when another app has focus, and the host reader exits when CAD closes. It never creates documents or touches geometry. Ctrl-C stops a manual bridge. Only one bridge runs per prefix.

The menu launcher turns this on automatically after starting the host Wine server. The bridge waits up to 15 minutes for CAD to come up, which covers the browser sign-in and Open hand-off, and logs to that launch's `logs/run-*/spacemouse.log` in the state directory. Set `SM4L_SPACEMOUSE=0` when launching if you don't want it.

Current defaults:

| Setting | Default |
| --- | --- |
| Pan | `0.00001` meters per input unit at 30 Hz |
| Pitch/yaw/roll | `0.0002` radians per input unit at 30 Hz |
| Zoom | `0.00016` log-factor per input unit at 30 Hz |
| Deadzone | `10` input units |
| Smoothing | `0.05` second low-pass time constant |
| Inverted axes | `rz`, for physical left/right cap tilt after the daemon's axis remapping |

The reader combines the latest input into updates at up to 30 Hz. Smoothing stops the moment you let go of the cap. View calls run inside CAD, and COM method IDs are cached. Each update turns off view refresh, restores whatever it was before, then asks for one redraw. The timer runs on CAD's UI thread with a reentrancy guard. That's how update time went from 194 ms remotely, to 80–100 ms in-process with separate redraws, to 14–18 ms with one batched redraw. Those numbers come from the reference machine's test geometry, not a big assembly. The add-in logs the average frame time every 30 updates to `C:\sm4l-spacemouse-addin.log`.

To try different speeds manually:

```bash
python3 -B addin/spacemouse.py --pan .000015 --rotation .0003 --zoom .0002 --smoothing .05 --invert rz
```

Stop any running manual bridge first. `--seconds` sets an optional test length. Leave it off for normal use. My first timed test ran out while I was still using it, which made it look like input just stopped.

The menu launcher also reads sensitivity from environment variables: `SM4L_SPACEMOUSE_PAN`, `SM4L_SPACEMOUSE_ROTATION`, `SM4L_SPACEMOUSE_ZOOM`, `SM4L_SPACEMOUSE_SMOOTHING` and `SM4L_SPACEMOUSE_INVERT`. For inversion, use comma-separated axis names from `x,y,z,rx,ry,rz`. An empty value turns inversion off.

## Sensitivity per device

The built-in defaults were tuned on the SpaceMouse Pro (`046d:c62b`). The SpaceMouse Wireless (USB `256f:c63a`) feels right at twice those values. Set that per device with a systemd drop-in for the bridge unit, so the change lives in your user units and survives `bin/install_units.sh`:

```bash
mkdir -p ~/.config/systemd/user/sm4l-spacemouse.service.d
cat > ~/.config/systemd/user/sm4l-spacemouse.service.d/sensitivity.conf <<'CONF'
[Service]
Environment=SM4L_SPACEMOUSE_PAN=.00002 SM4L_SPACEMOUSE_ROTATION=.0004 SM4L_SPACEMOUSE_ZOOM=.00032
CONF
systemctl --user daemon-reload
systemctl --user restart sm4l-spacemouse.service
```

The values are the Pro defaults doubled. On the desktop replication, the frame time with the NVIDIA GPU was 3 to 4 ms. Pick values that feel right for your device, and keep the drop-in when you reinstall the units.

Tested devices:

| Device | USB ID | Sensitivity | Status |
| --- | --- | --- | --- |
| SpaceMouse Pro | `046d:c62b` | built-in defaults | Tested on the reference laptop |
| SpaceMouse Wireless | `256f:c63a` | drop-in above (2x) | Tested over USB on the desktop replication. Over Bluetooth it wasn't connected during the test |

## Add-in registration and updates

The current DLL is `C:\sm4l-spacemouse-v3.dll`, COM class `{BB75177C-6799-4F57-9B75-10931D6421F6}`. The reader writes the class path and `ThreadingModel=Apartment` under `HKLM\Software\Classes\CLSID`, and the title and description under `HKLM\Software\SolidWorks\Addins`. Those are prefix registry entries, not anything on your Linux system. It loads through the supported API and accepts either success or already-loaded. No vendor DLLs are modified for this.

SOLIDWORKS reads the startup switch from `HKCU\Software\SolidWorks\AddInsStartup\{clsid}`. When CAD exits with the add-in loaded, it sets that value to `1`, and the next start loads the add-in before the frame exists. `spacemouse.py` resets that value and the `HKLM` registration to `0` before every load and after the loader exits. The bridge runs from a user unit (`units/sm4l-spacemouse.service`) and attaches to each new `sldworks.exe` once it has been running for 60 seconds, so CAD started from the browser Open gets it too. The add-in waits for a stable, visible CAD frame before arming its timer.

I checked the `ISwAddin` interface ID and its IUnknown-based ABI against the installed `swpublished.tlb`. Registering the class under HKCU only gave a misleading "loaded" result without the connection callback. HKLM registration fixed that. CAD also hangs on to old DLL code after an add-in is unloaded, so the timer and redraw builds each got a new DLL and class identity, which let me keep my unsaved test part open. Restart CAD after updating the add-in. Swapping a loaded DLL doesn't mean the new code is running.

To remove it, set `SM4L_SPACEMOUSE=0` for launches, stop the reader, and disable **SM4L SpaceMouse** in Tools → Add-Ins. After closing CAD you can delete the two prefix registry keys above for this class, and the DLL if you want. The menu launcher works fine without it.

## Checks

```bash
python3 -B tests/test_spacemouse.py
python3 -B addin/spacemouse.py --check-view
```

The first check doesn't need the device. It covers axis mapping, bounds, smoothing, the immediate stop on release, and the packet format. The second needs an open part. It nudges the view, undoes it, and checks the zoom scale really changed. It doesn't save the part.

The newest motion packet lives at `C:\sm4l-spacemouse.bin`. It's replaced atomically and only readable by your user. The Windows side rejects packets that are malformed, non-finite, out of range, or older than 200 ms, applies each one once, and drops input while CAD isn't focused.

This builds on the [libspnav driver interface](https://github.com/FreeSpacenav/libspnav) and documented SOLIDWORKS view operations: [TranslateBy](https://help.solidworks.com/2022/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelView~TranslateBy.html), [ZoomByFactor](https://help.solidworks.com/2017/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.imodelview~zoombyfactor.html), [RotateAboutCenter](https://help.solidworks.com/2019/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelView~RotateAboutCenter.html) and [RollBy](https://help.solidworks.com/2024/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelView~RollBy.html).
