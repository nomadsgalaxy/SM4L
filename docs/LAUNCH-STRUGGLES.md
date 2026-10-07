# Launch and recovery struggles

## 2026-10-07, 15:57: what was actually wrong

After the crash, CAD didn't fail to start. It started without a display. Launched directly, CAD hands off to `SWXDesktopLauncher` and exits on purpose. It writes `Temp\SWExitApp\dlgData.txt` on the way out, and that's not a crash. The browser Open goes to the launcher service, and the service starts a backbone, which starts CAD again. That backbone and CAD loaded no `winex11`, so CAD got its license (`XWB`) and sat there invisible. The 14:50 copy that got stopped as "stalled" was one of these.

Wine runs services on a hidden desktop unless they're flagged interactive. Before the crash, a backbone started by hand on the desktop was still alive, so launches worked. The crash killed it, and every backbone after that came from the service and was headless. Swapping in an interactive backbone doesn't stick, because the service makes a new one for every request.

Setting the service `Type` to `0x110` (adding `SERVICE_INTERACTIVE_PROCESS`) and restarting the prefix fixed it. The next launch put the backbone and CAD on the visible desktop with the splash and main window. The replication guide's step 8 now includes it.

Two more things from this round. A direct launch can briefly start two launcher chains, and with them two CAD copies, so keep watching for a second instance. Also, the lock in `launch_proton.sh` stays held while the first launch's UMU container is alive, and that refused a relaunch even though no CAD was running.

## 2026-10-07 — the relaunch struggles after the desktop crash

The working part was saved before testing. Multiple later test launches were left running; that was a mistake. I reported RAM and swap exhaustion at 14:41:41, systemd-oomd killing KWin, and Xwayland using about 10 GB RAM plus 15 GB swap. Those allocation figures come from my crash report; the precise leak still needs profiling. Stopping the dedicated prefix cleared all CAD copies and restored about 20 GB available RAM.

The desktop restart changed XAUTHORITY. The old context produced Invalid MIT-MAGIC-COOKIE-1. We retrieved the current desktop environment and verified the dedicated Firefox Windows identity before continuing. One controlled Open started one CAD process with correct authentication, but no native windows or display-driver module. Memory stabilized around 11 GB available; Xwayland stayed near 38 MB in that short sample. Stopped that instance before replaying the pending vendor request interactively.

I saw the interactive launcher and followed its browser prompts. The service-created tray lacked DSLauncherTray. Replacing the tray and backbone with interactive copies using the current service's pipe arguments restored DSLauncherTray. That fixed a prerequisite, but did not establish a successful CAD launch. Another Open reached the service, whose log recorded Execute failed with subprocess return code 70. CAD did not start. HTTP 200, an Open button, and tray registration each verify only one stage.

The newest failed service child had already exited. A later replay used the remaining live earlier request, not a confirmed fresh request from the newest click. Its authentication may need renewal; do not claim that replay worked. My latest click was part of the existing launcher flow. The latest check found no CAD processes, about 19 GB available RAM, and about 23 GB free swap. Continue diagnosing this handoff; do not start another direct CAD copy while it is pending.

The shared wrapper now checks pgrep and takes a nonblocking lock before launching CAD or its vendor launchers. Browser service launches bypass it. The persistent Wine server initially inherited descriptor 9 and retained the lock; server and background helpers now close that descriptor. Both refusal paths and non-inheritance passed the runnable launcher test. These changes are in private SM4L as 52eb12b and 9d6db19; earlier handoff findings are a56e4dc.

The hidden save was a Move Confirmation dialog at x=8600, with Performance Evaluation behind it. Moving them over CAD let me save and close. The UI helper now centers over the owner's rectangle rather than Wine's wrong monitor area; placement tests pass, but a new automatic recovery event remains unverified. ClientSideGraphics=N caused a black launch prompt and was rolled back. Feature-tree suppression only deferred rebuild cost. No reliable permanent performance improvement is claimed. Native KDE save integration remains open.

This records session observations and my confirmations, not independent certification. Private tickets, cookies, pipe arguments and raw logs stay out of the repo and vault.
