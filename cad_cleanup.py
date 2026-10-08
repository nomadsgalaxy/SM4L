#!/usr/bin/env python3
"""Close the SOLIDWORKS leftovers that stay behind after sldworks.exe exits (the launcher chain with its
WebView2 processes, CATSTART, the view server, the process monitor, the exit helper).
Only processes of THIS prefix are touched (WINEPREFIX in /proc/<pid>/environ), and only these:
the programs in TARGETS, the WebView2 processes whose --webview-exe-name is the launcher or CAD, and the conhost /
WebView2 / CEF children of those. The service side that the browser Open needs (services.exe, svchost, winedevice,
plugplay, rpcss, explorer, 3DEXPERIENCELauncher, the tray, the backbone, the license service) is never in the list.
It waits until sldworks.exe has been gone for IDLE seconds, and it does nothing while a launcher younger than
MIN_AGE seconds that started after CAD closed is running, because that is a sign-in in progress.
Kill switch: create <state>/cleanup-off, or start the bridge with SM4L_CLEANUP=0.
Run as `cad_cleanup.py --dry-run` to see what it would close right now."""
import os, re, signal, sys, time
from pathlib import Path

LAUNCHERS = {'swxdesktoplauncher.exe', 'enoplmcsaclient.exe'}   # the sign-in client and the launcher it starts
TARGETS = LAUNCHERS | {'catstart.exe', 'viewserverv6.exe', 'sldprocmon.exe', 'sldexitapp.exe'}
WEBVIEW = 'msedgewebview2.exe'
WEBVIEW_OWNERS = ('--webview-exe-name=swxdesktoplauncher.exe', '--webview-exe-name=sldworks.exe')
CHILDREN_OK = {'conhost.exe', WEBVIEW, 'swcefsubproc.exe'}   # taken only below a target (Linux parent chain)
CAD = 'sldworks.exe'
IDLE = 10          # seconds with no sldworks.exe before cleaning
MIN_AGE = 180      # a launcher younger than this that started after CAD closed is protected (sign-in)
TERM_WAIT = 3      # seconds between SIGTERM and SIGKILL

def exe_name(cmdline):
    """File name of the Windows program in a Wine process's command line, lower case ('' when it has none)."""
    m = re.match(r'"?(.*?\.exe)', cmdline, re.I)
    return re.split(r'[\\/]', m.group(1))[-1].lower() if m else ''

def name_of(raw):
    """Program name from a raw /proc/<pid>/cmdline. Besides '<path>\\x.exe args', accepts the form Wine gives the
    launcher child of ENOPLMCSAClient: empty argv[0] and the bare word SWXDesktopLauncher as argv[1]."""
    argv = raw.split(b'\0')
    if len(argv) > 1 and argv[0] == b'' and argv[1] == b'SWXDesktopLauncher':
        return 'swxdesktoplauncher.exe'
    return exe_name(raw.replace(b'\0', b' ').decode('latin-1').strip())

def read_procs(prefix_dirs, proc='/proc'):
    """List the Wine programs of this prefix: dicts with pid, ppid, name, cmd (lower case), age (seconds)."""
    want = {os.path.realpath(d) for d in prefix_dirs}
    hertz = os.sysconf('SC_CLK_TCK')
    uptime = float(Path(proc, 'uptime').read_text().split()[0])
    out = []
    for pid in filter(str.isdigit, os.listdir(proc)):
        try:
            raw = Path(proc, pid, 'cmdline').read_bytes()
            cmd = raw.replace(b'\0', b' ').decode('latin-1').strip()
            name = name_of(raw)
            if not name:
                continue
            env = Path(proc, pid, 'environ').read_bytes().split(b'\0')
            if not any(e.startswith(b'WINEPREFIX=') and os.path.realpath(e[11:].decode(errors='replace')) in want for e in env):
                continue
            stat = Path(proc, pid, 'stat').read_text()
            fields = stat[stat.rindex(')') + 2:].split()
            out.append(dict(pid=int(pid), ppid=int(fields[1]), name=name, cmd=cmd.lower(),
                            age=uptime - int(fields[19]) / hertz))
        except (OSError, ValueError, IndexError):
            continue
    return out

def plan(procs, last_exit_age, idle=IDLE, min_age=MIN_AGE):
    """Return (list of procs to close, reason it is empty).
    last_exit_age: seconds since sldworks.exe was last seen exiting, or None when this run never saw it exit."""
    if any(p['name'] == CAD for p in procs):
        return [], 'CAD is running'
    if last_exit_age is not None and last_exit_age < idle:
        return [], 'CAD exited %.0f s ago, waiting' % last_exit_age
    by_pid = {p['pid']: p for p in procs}
    targets = {p['pid'] for p in procs if p['name'] in TARGETS or (p['name'] == WEBVIEW and any(o in p['cmd'] for o in WEBVIEW_OWNERS))}
    for p in procs:                                   # children (and grandchildren) of a target
        if p['name'] in CHILDREN_OK and p['pid'] not in targets:
            up, hops = p['ppid'], 0
            while up in by_pid and hops < 8:
                if up in targets:
                    targets.add(p['pid']); break
                up, hops = by_pid[up]['ppid'], hops + 1
    chosen = [by_pid[pid] for pid in targets]
    for p in chosen:
        started_after_exit = last_exit_age is None or p['age'] < last_exit_age
        if p['name'] in LAUNCHERS and p['age'] < min_age and started_after_exit:
            return [], 'a launcher started %.0f s ago (sign-in in progress?)' % p['age']
    return chosen, 'nothing to close' if not chosen else ''

class Cleaner:
    def __init__(self, state, log=None, dry_run=False):
        self.state = Path(state)
        self.prefix_dirs = [self.state / 'prefix', self.state / 'prefix' / 'pfx']
        self.log = Path(log) if log else self.state / 'cleanup.log'
        self.dry_run = dry_run
        self.cad_running = False
        self.exit_time = None
        self.quiet_reason = None
        self.min_age = MIN_AGE
        self.next_ok = 0

    def say(self, text):
        line = time.strftime('%F %T ') + text
        print(line, flush=True)
        try:
            with self.log.open('a') as f:
                f.write(line + '\n')
        except OSError:
            pass

    def disabled(self):
        return os.environ.get('SM4L_CLEANUP') == '0' or (self.state / 'cleanup-off').exists()

    def step(self, wait=time.sleep):
        """One pass: remember CAD exits, then close leftovers when it is safe. Returns the list it closed."""
        procs = read_procs(self.prefix_dirs)
        running = any(p['name'] == CAD for p in procs)
        if self.cad_running and not running:
            self.exit_time = time.monotonic()
        self.cad_running = running
        if self.disabled() or time.monotonic() < self.next_ok:
            return []
        since = None if self.exit_time is None else time.monotonic() - self.exit_time
        chosen, reason = plan(procs, since, min_age=self.min_age)
        if not chosen:
            if reason != self.quiet_reason and not reason.startswith(('CAD exited', 'nothing')):
                self.say('cleanup idle: ' + reason)
            self.quiet_reason = reason
            return []
        self.quiet_reason = None
        names = ', '.join('%s pid %d age %.0fs' % (p['name'], p['pid'], p['age']) for p in chosen)
        if self.dry_run:
            self.say('cleanup would close: ' + names)
            return chosen
        self.say('cleanup closing: ' + names)
        self.next_ok = time.monotonic() + 20
        for p in chosen:
            try:
                os.kill(p['pid'], signal.SIGTERM)
            except OSError:
                pass
        wait(TERM_WAIT)
        alive = {p['pid'] for p in read_procs(self.prefix_dirs)}
        for p in chosen:
            if p['pid'] in alive:
                try:
                    os.kill(p['pid'], signal.SIGKILL)
                    self.say('cleanup needed SIGKILL for %s pid %d' % (p['name'], p['pid']))
                except OSError:
                    pass
        return chosen

if __name__ == '__main__':
    if '--dry-run' not in sys.argv:
        sys.exit('cad_cleanup.py only runs inside the bridge; use --dry-run to see what it would close')
    state = os.environ.get('SOLIDWORKS_PROTON_STATE') or os.path.join(
        os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'solidworks-proton')
    procs = read_procs(Cleaner(state).prefix_dirs)
    chosen, reason = plan(procs, None)
    print('would close:' if chosen else reason, *('%s pid %d age %.0fs' % (p['name'], p['pid'], p['age']) for p in chosen))
    names = {p['pid']: p['name'] for p in procs}
    for p in procs:
        if p['name'] == 'conhost.exe' and p['pid'] not in {c['pid'] for c in chosen}:
            print('note: conhost pid %d is not below a close target (parent pid %d = %s); left alone' % (p['pid'], p['ppid'], names.get(p['ppid'], 'not a Wine program')))
