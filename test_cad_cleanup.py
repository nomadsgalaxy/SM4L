"""Check which leftovers cad_cleanup closes and which it never touches (pure plan checks, then real fake processes).
The fake processes are started by this test with a made-up WINEPREFIX under a temp directory; nothing else is touched."""
import os, signal, subprocess, sys, tempfile, time
from pathlib import Path
import cad_cleanup as c

def P(pid, ppid, name, age=600, cmd=''):
    return dict(pid=pid, ppid=ppid, name=name, cmd=(cmd or name).lower(), age=age)

assert c.exe_name('"C:\\Program Files\\X\\ViewServerV6.exe" -Embedding') == 'viewserverv6.exe'
assert c.exe_name('C:\\Program Files\\Dassault Systemes\\SOLIDWORKS\\sldworks.exe') == 'sldworks.exe'
assert c.exe_name('python3 /usr/bin/thing') == ''
assert c.name_of(b'\0SWXDesktopLauncher\0-Url=x\0') == 'swxdesktoplauncher.exe'       # Wine's rewritten launcher child
assert c.name_of(b'C:\\a\\SWXDesktopLauncher.exe\0-Url=x\0') == 'swxdesktoplauncher.exe'
assert c.name_of(b'SWXDesktopLauncher\0-Url=x\0') == '' and c.name_of(b'python3\0x\0') == ''

keep = [P(1, 0, 'services.exe'), P(2, 1, 'svchost.exe'), P(3, 1, 'winedevice.exe'), P(4, 1, 'explorer.exe'),
        P(5, 1, '3dexperiencelauncher.exe'), P(6, 1, 'dslaunchertray.exe'), P(7, 1, 'fnplicensingservice64.exe'),
        P(8, 6, 'conhost.exe')]                                  # conhost below the tray: not ours
left = [P(20, 1, 'swxdesktoplauncher.exe'), P(21, 20, 'conhost.exe'),
        P(22, 20, 'msedgewebview2.exe', cmd='msedgewebview2.exe --webview-exe-name=SWXDesktopLauncher.exe'),
        P(23, 22, 'msedgewebview2.exe', cmd='msedgewebview2.exe --type=renderer'), P(24, 1, 'catstart.exe'),
        P(25, 1, 'viewserverv6.exe'), P(26, 1, 'sldprocmon.exe'), P(27, 1, 'sldexitapp.exe')]
other_webview = P(30, 6, 'msedgewebview2.exe', cmd='msedgewebview2.exe --webview-exe-name=tray.exe')
def ids(l): return sorted(p['pid'] for p in l)

# CAD running or only just closed: nothing.
assert c.plan(keep + left + [P(40, 1, 'sldworks.exe')], 100)[0] == []
assert c.plan(keep + left, 5)[0] == []
# Closed long enough: the leftovers and their children, never the service side or foreign WebView2.
chosen, _ = c.plan(keep + left + [other_webview], 60)
assert ids(chosen) == [20, 21, 22, 23, 24, 25, 26, 27], ids(chosen)
# A launcher that started after CAD closed and is young = a sign-in in progress: touch nothing.
assert c.plan(keep + left, 60)[0] != [] and c.plan(keep + [P(50, 1, 'swxdesktoplauncher.exe', age=20)] + left, 60)[0] == []
# The same young launcher is fine once it is older than min_age or started before CAD closed.
assert c.plan(keep + [P(50, 1, 'swxdesktoplauncher.exe', age=200)], 60)[0] != []
assert c.plan(keep + [P(50, 1, 'swxdesktoplauncher.exe', age=70)], 60)[0] != []   # older than the exit
# This run never saw CAD exit: only old leftovers are closed, a young launcher blocks.
assert ids(c.plan(keep + [P(50, 1, 'catstart.exe')], None)[0]) == [50]
assert c.plan(keep + [P(50, 1, 'swxdesktoplauncher.exe', age=30)], None)[0] == []
assert c.plan(keep, 60)[0] == []

# Real fake processes: started by this test, with a made-up prefix.
with tempfile.TemporaryDirectory() as tmp:
    state = Path(tmp) / 'state'; pfx = state / 'prefix' / 'pfx'; pfx.mkdir(parents=True)
    foreign = Path(tmp) / 'other-prefix'; foreign.mkdir()
    def fake(name, prefix, ignore_term=False):
        trap = 'trap "" TERM; ' if ignore_term else ''
        return subprocess.Popen(['bash', '-c', f'{trap}exec -a "C:\\\\x\\\\{name}" sleep 600'], env=dict(os.environ, WINEPREFIX=str(prefix)),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cad = fake('sldworks.exe', pfx)
    target = fake('SWXDesktopLauncher.exe', pfx); stubborn = fake('CATSTART.exe', pfx, ignore_term=True)
    svc = fake('services.exe', pfx); stranger = fake('ViewServerV6.exe', foreign)
    procs = [cad, target, stubborn, svc, stranger]
    try:
        time.sleep(0.5)
        cl = c.Cleaner(state, log=Path(tmp) / 'cleanup.log'); cl.min_age = 0
        assert cl.step() == []                                    # CAD running
        cad.terminate(); cad.wait(); time.sleep(0.2)
        assert cl.step() == []                                    # just exited: waiting
        (state / 'cleanup-off').write_text('')
        cl.exit_time -= 60
        assert cl.step() == []                                    # kill switch
        (state / 'cleanup-off').unlink()
        dry = c.Cleaner(state, log=Path(tmp) / 'dry.log', dry_run=True); dry.exit_time = time.monotonic() - 60; dry.min_age = 0
        assert sorted(p['name'] for p in dry.step()) == ['catstart.exe', 'swxdesktoplauncher.exe'] and target.poll() is None
        closed = cl.step(wait=lambda s: time.sleep(0.5))
        assert sorted(p['name'] for p in closed) == ['catstart.exe', 'swxdesktoplauncher.exe'], closed
        target.wait(5); stubborn.wait(5)
        assert target.returncode == -signal.SIGTERM and stubborn.returncode == -signal.SIGKILL
        assert svc.poll() is None and stranger.poll() is None     # service side and foreign prefix untouched
        assert 'needed SIGKILL for catstart.exe' in (Path(tmp) / 'cleanup.log').read_text()
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill(); p.wait()
print('cad_cleanup plan, protection, kill switch, SIGTERM/SIGKILL and prefix scoping checks passed')
