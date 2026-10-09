# Troubleshooting

Each problem below lists what you'll see, the usual cause, and what to do. Start with the first check in each section, because it often tells you which case you're in.

Keep the prefix's logs local. They can contain sign-in URLs and tickets.

## Platform install fails with 1603

**You see:** the platform installer fails with error 1603. `Errors.log` names `SWXDesktopInsSWK:SWXDesktopInsSWKInstall`, and the failure is at `InstallSpatialIOP`, with `SHBindToObject failed - HRESULT: 0x80070002`, then "Unzip failed", then a rollback.

**Usual cause:** the platform installer was set to automatic (`SWXDesktopInsUpgradeType_SingleAutomatic`). That makes it run the SOLIDWORKS MSI in the same pass, and the Windows ZIP-shell path fails there. The first run writes `SWXDesktopInsData.ini` under the install's `win_b64\resources` folder, with `SWXDesktopInsUpgradeTypeLiteBefore=SWXDesktopInsUpgradeTypeLite_Automatic`. Every rerun or resume reads that file and forces automatic again, whatever you choose.

**Do this:** rerunning doesn't fix it, and a resumed run also fails earlier, with "Failed to expand expression ... CSIDL_COMMON_DOCUMENTS" and exit code 3. Set the old prefix aside (rename it, don't delete it), then create a fresh prefix and redo [INSTALL.md](INSTALL.md) steps 5 and 6. In the platform installer, choose **updates on demand** (MultiManual) this time. Confirm the choice in `Journal.log` under the `InstallData` folder: it should show `MultiManual=true`. Deleting only the ini is untested, so don't rely on it. Then install CAD through Installation Manager in [INSTALL.md](INSTALL.md), step 8.

## After a CAD crash, nothing starts cleanly

**You see:** CAD dies about 25 seconds after it starts, or new launches stall, after an earlier crash.

**Usual cause:** state left in the prefix by the crash. On the reference machine, a restart of the prefix cleared it. The exact state wasn't identified.

**Do this:**

1. Close every CAD window. Make sure no `sldworks.exe` is still running.
2. Stop the prefix's server, once, with the wineserver for that prefix:

   ```bash
   WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
   ```

3. Start CAD again with `"$LAUNCH" "$CAD_DIR/sldworks.exe"`, or click **Open** once.

Don't click **Open** repeatedly while a launch is still running. Each click starts another launch chain, and the chains compete with each other. Stuck chains time out on their own after about three and a half minutes.

## CAD hangs on exit

**You see:** CAD closes its windows, but `sldworks.exe` stays running, or its main thread stops responding.

**Usual cause:** unknown. It happened once on the reference machine, with a loader-lock timeout.

**Do this:**

- The leftover cleanup in `addin/cad_cleanup.py` handles it. After CAD exits, it sends `SIGTERM` and then `SIGKILL` to a `sldworks.exe` whose main thread is a zombie for 45 seconds, and it cleans up this prefix's orphaned Wine programs. Check `cleanup.log` in the state directory.
- Stopping the prefix with `wineserver -k` didn't end the hung process on the reference machine.
- Never kill a CAD that's still open with a visible window. The cleanup doesn't do that either, because an idle or minimised CAD can hold unsaved work.

The add-in's exit path is newer, and it hasn't been confirmed on a real exit yet. If the hang returns, note the time and check the cleanup log.

## Browser Open does nothing and a terminal flashes

**You see:** you click **Open** in the browser, and a terminal flashes but nothing else happens.

**Usual cause:** nothing is listening on `127.0.0.1:20250`, because the launcher tray isn't running.

**Do this:**

```bash
curl --head --max-time 5 http://127.0.0.1:20250/
systemctl --user start sm4l-launcher.service
```

If the endpoint still doesn't answer, start the tray by hand as shown in [INSTALL.md](INSTALL.md), step 11, and click **Open** once.

Starting `sldworks.exe` directly doesn't skip the platform. CAD hands off to `SWXDesktopLauncher`, which needs the browser's **Open** click.

## Open leads to a CAD that never shows a window

**You see:** the launcher reports success, and CAD runs, but no window appears.

**Usual cause:** the launcher service wasn't marked interactive, so Wine ran it on a hidden desktop.

**Do this:** check the service type, and set it if it's wrong:

```bash
pwine reg.exe query 'HKLM\System\CurrentControlSet\Services\3DEXPERIENCELauncher' /v Type
```

It should be `0x110`. Step 11 in [INSTALL.md](INSTALL.md) sets it. Stop the prefix's server after changing it, and close CAD first.

## XAUTHORITY errors after a desktop restart

**You see:** `Invalid MIT-MAGIC-COOKIE-1`, or a launch that can't open a display.

**Usual cause:** KWin restarted, so the `XAUTHORITY` file name changed.

**Do this:**

- Restart the launcher unit, which reads the current display variables from the session: `systemctl --user restart sm4l-launcher.service`.
- For a manual launch, use the current session's values. Don't reuse an old `XAUTHORITY` path.

## Checkbox and radio labels are missing

**You see:** the PropertyManager's checkboxes and radio buttons appear without their labels.

**Usual cause:** the prefix's Windows theme is on.

**Do this:** turn the theme off, as in [INSTALL.md](INSTALL.md), step 14. It's the setup that worked on the reference machine. The result is a classic, flatter look.

After a prefix update or a recreated prefix, run step 14 again. `setup/ensure_theme_off.py` is meant to re-apply the setting before each start, but that's pending a live check.

## The original CATSysTS.dll is missing

**You see:** the directory-compat step reports that the backup `CATSysTS.dll.pre-swcompat` is missing, or a rollback has no file to restore.

**Usual cause:** the backup was never created, or it was moved or deleted. Installs made before `setup/apply_directory_compat.py` existed kept the original elsewhere.

**Do this:** look for the original in both places:

- Next to the platform's `CATSysTS.dll`, as `CATSysTS.dll.pre-swcompat`.
- Older installs may have it at `$SOLIDWORKS_PROTON_STATE/directory-compat/CATSysTS.original.dll`.

Check the file's SHA256 against the original before you restore it. Don't restore an unknown file.

## Saving or opening from the 3DEXPERIENCE platform misbehaves

**You see:** save, open, or 3DEXPERIENCE tab and task pane features fail or behave oddly, after the PLM connector hook change.

**Usual cause:** the connector's window tracking is off, because its hook was removed. The add-in does this by default.

**Do this:** if you use the 3DEXPERIENCE features, turn the release off. Create the file `C:\sm4l-unhook-pdm-off` in the prefix's `drive_c` folder, then restart CAD. The hook comes back on the next start. The release hasn't been tested for these workflows, so report what fails.

## Section headers are missing or wiped

**You see:** PropertyManager headers such as Type, To Fillet, Parameters or Options disappear, especially after a drag or resize.

**Usual cause:** the header hook in the UI add-in isn't running.

**Do this:** check that `sm4l-ui-compat.service` is active. It runs the add-in that keeps the headers. Enable it as in [INSTALL.md](INSTALL.md), step 12.

If the headers still wipe, the add-in's kill switches (`C:\sm4l-hdr-nozorder-off` and `C:\sm4l-hdr-clamp-off`) can isolate which part is involved. Their default is on.

## dotnet48 fails with status 5, or the prefix registry is tiny

**You see:** `winetricks -q dotnet48` (or `dotnet40`) fails with status 5, and the prefix's registry files are far smaller than they should be. On the desktop deploy, `user.reg` and the system registry were about 254 KB, where a healthy prefix had about 3.7 MB.

**Usual cause:** the persistent host Wine server started before the prefix existed, so the server wrote an empty or partial registry. The launcher also didn't return after short commands, which hid the exit codes.

**Do this:** a prefix whose `system.reg` lacks the `[Software\\Classes\\CLSID]` keys is broken. It's about 250 KB where a healthy one is about 4 MB. A healthy fresh prefix has about 4 MB of `system.reg` with the `[Software\\Classes\\CLSID]` keys. Stop the prefix's server, then rename `$SOLIDWORKS_PROTON_STATE/prefix` aside, for example to `prefix.broken-<date>`, and run `setup.sh` again. The launcher creates a fresh prefix itself. Keep the renamed copy until you're sure you don't need it. Don't delete it, because it can hold your own files. `setup.sh --plan` reports the prefix check.

Judge the .NET step by `RegAsm.exe` existing, not by the exit status of `umu-run` or `winetricks`, because those exit codes aren't reliable here.

## setup.sh says the media is incomplete

**You see:** `setup.sh` stops at the media step and prints the reason.

**Usual cause:** a file is missing from one of the seven numbered folders, the ZIP was extracted into the wrong place, or the `setup.exe` hash doesn't match the supported release.

**Do this:** run `python3 -B setup/media_check.py "$MEDIA_1"` to see the failing file or hash. Re-extract the ZIP from the vendor download if a file is missing. Don't patch a file that fails the hash, because the patches refuse builds they don't know. The full SHA256 pass, `setup/media_check.py "$MEDIA_1" hashes`, is slower and optional.

## Save As 3MF crashes CAD

**You see:** CAD crashes during Save As 3MF.

**Usual cause:** Wine's builtin msxml3 mishandles document references in the printing path.

**Do this:** install the native msxml6 override for CAD only, as in [INSTALL.md](INSTALL.md), step 15. It was verified once on the reference machine, so keep the file a backup until it passes again.

## The login page is blank

**You see:** the embedded sign-in page renders as a blank panel.

**Usual cause:** the WebView renderer or its launch flags.

**Do this:** check the Windows-identifying Firefox profile and the WebView flags in [INSTALL.md](INSTALL.md), steps 9 and 10. The embedded browser panels still flash in some cases, which is an open problem.

## HTTP 403 or licence error 1002 at sign-in

**You see:** a 403 from the server, or licence error 1002 when CAD starts.

**Usual cause:** the account, tenant or assigned role, not the setup.

**Do this:** check your account, tenant and role assignment with the vendor. Don't assume a purchased role is assigned, and don't patch a licence result. This project doesn't change licensing.

## CAD opens with a black viewport

**You see:** menus and the feature tree render, but the part viewport is black.

**Usual cause:** Enhanced graphics performance is on.

**Do this:** turn it off in **Tools → Options → System Options → Performance**, apply, close CAD normally, and start it again. [INSTALL.md](INSTALL.md), step 16, has the details.

## A launch is refused, or a second CAD starts

**You see:** a new launch is refused with a lock message, or two CAD copies appear.

**Usual cause:** a launch from earlier still holds the wrapper's lock, or two launch chains are running.

**Do this:** close CAD and stop the prefix's server, then launch once. Check the process list before starting another copy:

```bash
pgrep -af 'sldworks|SWXDesktopLauncher|CATSTART'
```

## Where the logs are

- Launch logs: under the state directory, in a `logs/run-*` folder for each launch.
- Cleanup decisions: `cleanup.log` in the state directory.
- Add-in logs inside the prefix: `C:\sm4l-spacemouse-addin.log` and `C:\sm4l-ui-compat.log`.
- SOLIDWORKS writes `SolidWorksPerformance.log` on each run. It lists each add-in load and marks the last one that crashed.

Remove any log that contains a sign-in URL or a ticket before you share it.
