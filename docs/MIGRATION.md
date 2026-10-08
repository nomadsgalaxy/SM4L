# Moving an existing setup to the new layout

The repository moved files into `bin/`, `setup/`, `addin/`, `tests/` and `experiments/`. The unit files in `units/` are now templates. The guide moved from `docs/REPLICATE.md` to `docs/INSTALL.md`. There are no compatibility symlinks, so an existing setup must be switched over deliberately.

Two things in your user session refer to the old checkout path, and both must change:

- The systemd user units in `~/.config/systemd/user/`. They point at the old `launch_service.sh` and `spacemouse.py`.
- The Wine browser registration in the prefix: `HKCU\Software\Wine\WineBrowser` `Browsers`. It stores the absolute path of `open_windows_firefox.sh`.

The menu entry also stores an absolute path, so it needs reinstalling as well. `bin/register_paths.py` does both.

The live prefix's `Browsers` value currently points at the parent folder, `.../apps/solidworks/open_windows_firefox.sh`, not at the SM4L checkout. Migrating re-registers it either way.

**Status:** the switch-over is done on the reference laptop. `main` was fast-forwarded to the reorganized layout, the units were reinstalled from `bin/`, `bin/register_paths.py` has run, and `setup.sh --plan` reports nothing left to do. The steps below are kept for anyone moving an older checkout.

## Before you start

- Close CAD. Make sure no `sldworks.exe`, `SWXDesktopLauncher`, `CATSTART` or `ViewServer` process is left running.
- Commit or stash any local changes in the old checkout. Nothing in this migration should be run on a dirty tree.

## Steps

Run these from the old checkout unless the step says otherwise.

1. Stop the three units:

   ```bash
   systemctl --user stop sm4l-launcher.service sm4l-spacemouse.service sm4l-ui-compat.service
   ```

2. Stop the prefix's Wine server, once:

   ```bash
   WINEPREFIX="$SOLIDWORKS_PROTON_STATE/prefix/pfx" "$PROTONPATH/files/bin/wineserver" -k
   ```

3. Update the checkout to the reorganized layout. Merge the `reorg` branch, or check out the commit that contains it.

4. Render the unit templates into your user unit directory:

   ```bash
   cd "$SM4L_ROOT"
   bin/install_units.sh
   ```

   The installer replaces the old unit files and removes stale `sm4l-*` units. It doesn't restart anything. Units that are running keep their old paths until they restart, which is why step 1 stopped them.

5. Register the Wine browser handler and the menu entry at the new paths:

   ```bash
   python3 -B bin/register_paths.py --check
   python3 -B bin/register_paths.py
   desktop-file-validate "$HOME/.local/share/applications/SM4L-solidworks.desktop"
   ```

   The script writes the prefix's `Browsers` value to `bin/open_windows_firefox.sh`, and it reinstalls the menu entry to point at `bin/launch_solidworks.sh`. `--check` shows what it would change first.

7. Start the units again:

   ```bash
   systemctl --user enable --now sm4l-launcher.service
   systemctl --user enable --now sm4l-spacemouse.service sm4l-ui-compat.service
   ```

   Enable the SpaceMouse unit only if you use the SpaceMouse.

8. Check the launcher endpoint, then open CAD from the menu entry once:

   ```bash
   curl --head --max-time 5 http://127.0.0.1:20250/
   ```

## What didn't move

- The prefix, its registry settings, the installed CAD, the platform and the login profile stay where they are. Only the paths that point into the checkout change.
- The `ThemeActive` setting, the header-guard DLL, the native msxml6 files and the WebView2 settings all stay as they are. Their steps are in [INSTALL.md](INSTALL.md).
- `REPLICATE.md` is gone. [INSTALL.md](INSTALL.md) replaces it, with the same steps in a single order.

## Rolling back

Check out the old commit, then repeat steps 1, 4 and 6 against the old `units/` and `bin/` paths. Register the old `open_windows_firefox.sh` path again in step 5. The old launcher paths in the units and the menu entry come back the same way.
