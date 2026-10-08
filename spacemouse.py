#!/usr/bin/env python3
"""Connect the existing Linux spacenavd socket to SOLIDWORKS view navigation."""
import argparse
import ctypes as C
from ctypes.util import find_library
import fcntl
import math
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import time

PACKET = struct.Struct('<IIQ6d')
MAGIC = 0x534D344C

class Motion(C.Structure):
    _fields_ = [(n, C.c_int) for n in ('type', 'x', 'y', 'z', 'rx', 'ry', 'rz')] + [('period', C.c_uint), ('data', C.POINTER(C.c_int))]

class Button(C.Structure):
    _fields_ = [(n, C.c_int) for n in ('type', 'press', 'bnum')]

class Event(C.Union):
    _fields_ = [('type', C.c_int), ('motion', Motion), ('button', Button), ('padding', C.c_byte * 48)]

def values(axes, dt, pan, rotation, zoom, deadzone, signs):
    """Produce bounded view deltas; daemon already normalizes the device axes."""
    if len(axes) != 6 or len(signs) != 6 or not all(math.isfinite(x) for x in (*axes, dt, pan, rotation, zoom)):
        raise ValueError('Six finite axes and finite sensitivities are required')
    a = [max(-1000, min(1000, x)) * sign if abs(x) > deadzone else 0 for x, sign in zip(axes, signs)]
    factor = max(0, min(dt, .05)) * 30
    clamp = lambda x, limit: max(-limit, min(limit, x))
    return (clamp(a[0]*pan*factor, .05), clamp(a[1]*pan*factor, .05),
            math.exp(clamp(-a[2]*zoom*factor, .15)),
            clamp(a[3]*rotation*factor, .1), clamp(a[4]*rotation*factor, .1), clamp(a[5]*rotation*factor, .1))

def smooth(previous, axes, dt, seconds, deadzone):
    if not any(abs(x) > deadzone for x in axes):
        return [0.0]*6  # Release stops immediately instead of letting the camera drift.
    alpha = 1 if not seconds else -math.expm1(-max(0, dt)/seconds)
    target = [x if abs(x) > deadzone else 0 for x in axes]
    return [old+(new-old)*alpha for old, new in zip(previous, target)]

def publish(path, seq, motion):
    stamp = time.time_ns() // 100 + 116444736000000000  # Windows FILETIME epoch.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.sm4l-motion-', delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(PACKET.pack(MAGIC, seq & 0xffffffff, stamp, *motion))
            f.flush()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

def build(state, addin=False, ui=False):
    source = Path(__file__).with_name('spacemouse-view.c')
    stem = 'ui-compat' if ui else 'spacemouse-view'
    exe, obj = state/(stem+'.exe'), state/(stem+'.obj')
    if not exe.exists() or exe.stat().st_mtime_ns < source.stat().st_mtime_ns:
        subprocess.run(['clang', '--target=x86_64-pc-windows-msvc', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-builtin', '-c', str(source), '-o', str(obj)], check=True)
        libs = Path('/usr/lib/wine/x86_64-windows')
        subprocess.run(['lld-link', '/entry:entry', '/subsystem:console', '/nodefaultlib', '/machine:x64', '/out:'+str(exe.with_suffix('.new.exe')), str(obj), *(str(libs/('lib'+n+'.a')) for n in ('kernel32', 'ole32', 'oleaut32', 'user32', 'gdi32', 'uxtheme'))], check=True)
        os.replace(exe.with_suffix('.new.exe'), exe)
    if addin:
        dll = state/'prefix/pfx/drive_c'/('sm4l-ui-compat-v2.dll' if ui else 'sm4l-spacemouse-v3.dll')
        if not dll.exists() or dll.stat().st_mtime_ns < source.stat().st_mtime_ns:
            dll_obj = state/(stem+'-addin.obj')
            staged = state/(stem+'-addin.new.dll')
            subprocess.run(['clang', '--target=x86_64-pc-windows-msvc', '-DSM4L_ADDIN', *(['-DSM4L_UI_ADDIN'] if ui else []), '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-fno-builtin', '-c', str(source), '-o', str(dll_obj)], check=True)
            libs = Path('/usr/lib/wine/x86_64-windows')
            subprocess.run(['lld-link', '/dll', '/noentry', '/nodefaultlib', '/machine:x64', '/out:'+str(staged), str(dll_obj), *(str(libs/('lib'+n+'.a')) for n in ('kernel32', 'ole32', 'oleaut32', 'user32', 'gdi32', 'uxtheme'))], check=True)
            os.replace(staged, dll)
    return exe

def register(wine, env, ui=False):
    guid = '{BB75177C-6799-4F57-9B75-10931D6421FA}' if ui else '{BB75177C-6799-4F57-9B75-10931D6421F6}'
    classes = 'HKLM\\Software\\Classes\\CLSID\\'+guid+'\\InprocServer32'
    addin = 'HKLM\\Software\\SolidWorks\\Addins\\'+guid
    entries = [(classes, None, 'REG_SZ', r'C:\sm4l-ui-compat-v2.dll' if ui else r'C:\sm4l-spacemouse-v3.dll'),
               (classes, 'ThreadingModel', 'REG_SZ', 'Apartment'),
               (addin, None, 'REG_DWORD', '0'),
               (addin, 'Title', 'REG_SZ', 'SM4L UI compatibility' if ui else 'SM4L SpaceMouse'),
               (addin, 'Description', 'REG_SZ', 'Restore radio and checkbox labels' if ui else 'Linux SpaceMouse view navigation')]
    for key, name, kind, value in entries:
        subprocess.run([wine, 'reg.exe', 'add', key, *(['/v', name] if name else ['/ve']), '/t', kind, '/d', value, '/f'], env=env, check=True, stdout=subprocess.DEVNULL)
    disarm(wine, env)

def session_display():
    """DISPLAY/XAUTHORITY of the live session (XAUTHORITY changes whenever KWin restarts)."""
    env = dict(os.environ)
    out = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True).stdout
    for line in out.splitlines():
        key, _, value = line.partition('=')
        if key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
            env[key] = value
    return env

def frame_visible(pid, env):
    """True when the CAD process owns a large visible X window (the main frame, not the splash)."""
    out = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', pid], capture_output=True, text=True, env=env).stdout.split()
    for win in out:
        geometry = subprocess.run(['xdotool', 'getwindowgeometry', '--shell', win], capture_output=True, text=True, env=env).stdout
        size = dict(line.split('=', 1) for line in geometry.splitlines() if '=' in line)
        if int(size.get('WIDTH', 0) or 0) >= 640 and int(size.get('HEIGHT', 0) or 0) >= 480:
            return True
    return False

_frame_seen = {}

def settled_cad(seconds=15, fallback=90, stable=3):
    """Oldest sldworks.exe pid once it is safe to LoadAddIn into it: at least `seconds` old and its
    main frame visible on X for `stable` scans in a row. Without a usable xdotool/display (or if no
    frame ever shows), fall back to a plain age of `fallback` seconds."""
    pid = subprocess.run(['pgrep', '-xo', 'sldworks.exe'], capture_output=True, text=True).stdout.strip()
    if not pid:
        _frame_seen.clear()
        return ''
    age = subprocess.run(['ps', '-o', 'etimes=', '-p', pid], capture_output=True, text=True).stdout.strip()
    if not age.isdigit() or int(age) < seconds:
        return ''
    if int(age) >= fallback:
        return pid
    try:
        seen = _frame_seen[pid] = _frame_seen.get(pid, 0)+1 if frame_visible(pid, session_display()) else 0
    except (OSError, ValueError):
        return ''
    return pid if seen >= stable else ''

SM4L_ADDINS = ('{BB75177C-6799-4F57-9B75-10931D6421F6}', '{BB75177C-6799-4F57-9B75-10931D6421FA}')

def disarm(wine, env, ui=False):
    """Keep CAD from loading our add-ins by itself at startup.
    CAD flips the default value to 1 when it exits with an add-in loaded, and an exit by crash
    skips our post-exit reset. It reads the per-user HKCU AddInsStartup value at startup (HKLM Addins
    is the add-in list), so reset both hives for both add-ins, before every load and after exit."""
    for guid in SM4L_ADDINS:
        for key in ('HKLM\\Software\\SolidWorks\\Addins\\'+guid, 'HKCU\\Software\\SolidWorks\\AddInsStartup\\'+guid):
            subprocess.run([wine, 'reg.exe', 'add', key, '/ve', '/t', 'REG_DWORD', '/d', '0', '/f'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark', action='store_true', help='Time a redraw/rebuild and report feature timings; does not save or change dimensions')
    p.add_argument('--ui-only', action='store_true', help='Restore themed checkbox/radio painting without a SpaceMouse')
    p.add_argument('--check-view', action='store_true', help='Test navigation APIs on the active part, then reverse the movements')
    p.add_argument('--listen', action='store_true', help='Print device events without launching the CAD helper')
    p.add_argument('--seconds', type=float, default=0, help='Stop after this many seconds; zero runs until Ctrl-C')
    p.add_argument('--pan', type=float, default=os.environ.get('SM4L_SPACEMOUSE_PAN', '.00001'), help='Meters per axis unit at 30 Hz')
    p.add_argument('--rotation', type=float, default=os.environ.get('SM4L_SPACEMOUSE_ROTATION', '.0002'), help='Radians per axis unit at 30 Hz')
    p.add_argument('--zoom', type=float, default=os.environ.get('SM4L_SPACEMOUSE_ZOOM', '.00016'), help='Log zoom factor per axis unit at 30 Hz')
    p.add_argument('--smoothing', type=float, default=os.environ.get('SM4L_SPACEMOUSE_SMOOTHING', '.05'), help='Low-pass time constant in seconds; zero disables smoothing')
    p.add_argument('--deadzone', type=int, default=10)
    p.add_argument('--invert', default=os.environ.get('SM4L_SPACEMOUSE_INVERT', 'rz'), help='Comma-separated axes to invert: x,y,z,rx,ry,rz')
    args = p.parse_args()
    if not all(math.isfinite(n) and n >= 0 for n in (args.seconds, args.pan, args.rotation, args.zoom, args.smoothing)) or args.deadzone < 0:
        p.error('Sensitivities, duration and deadzone must be finite and nonnegative')
    names = ('x', 'y', 'z', 'rx', 'ry', 'rz')
    inverse = set(filter(None, args.invert.split(',')))
    if inverse - set(names):
        p.error('--invert accepts only x,y,z,rx,ry,rz')
    signs = [-1 if n in inverse else 1 for n in names]
    state = Path(os.environ.get('SOLIDWORKS_PROTON_STATE', str(Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'solidworks-proton')))
    prefix = state/'prefix/pfx'
    if not (prefix/'drive_c').is_dir():
        p.error('Initialize the SOLIDWORKS prefix first')
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEFSYNC='0', WINEESYNC='0', WINEDEBUG='-all')
    proton = Path(os.environ.get('PROTONPATH', str(Path.home()/'.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4')))
    command = [str(proton/'files/bin/wine64'), str(build(state, addin=not args.check_view and not args.benchmark and not args.listen, ui=args.ui_only))]
    if args.check_view or args.benchmark:
        return subprocess.call(command+['--benchmark' if args.benchmark else '--check-view'], env=env)
    if args.ui_only:
        with (state/'ui-compat.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 0
            attempts = {}
            while True:
                # Stay alive: CAD starts from the menu or from the browser (3DEXPERIENCE
                # launcher) and restarts. Never touch Wine until an instance exists, so
                # this cannot start a mismatched wineserver. At most 3 tries per instance.
                time.sleep(2)
                cad = settled_cad()
                if not cad or attempts.get(cad, 0) >= 3:
                    continue
                attempts[cad] = attempts.get(cad, 0)+1
                register(command[0], env, ui=True)
                try:
                    subprocess.call(command+['--load-ui-addin'], env=env)
                finally:
                    disarm(command[0], env, ui=True)
    lib = C.CDLL(find_library('spnav') or 'libspnav.so.0')
    lib.spnav_poll_event.argtypes = [C.POINTER(Event)]
    lib.spnav_dev_name.argtypes = [C.c_char_p, C.c_int]
    if lib.spnav_open() < 0:
        p.error('Cannot connect to spacenavd; start the system spacenavd service')
    lock = (state/'spacemouse.lock').open('a')
    child = None
    path = prefix/'drive_c/sm4l-spacemouse.bin'
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        name = C.create_string_buffer(256)
        lib.spnav_dev_name(name, len(name))
        if name.value:
            print(f'{name.value.decode(errors="replace")}: {lib.spnav_dev_axes()} axes, {lib.spnav_dev_buttons()} buttons', flush=True)
        else:
            print('Waiting for a SpaceMouse device to connect.', flush=True)
        if not args.listen:
            path.unlink(missing_ok=True)
        event = Event()
        next_scan = time.monotonic()+2
        attempts = {}
        start = previous = last_motion = time.monotonic()
        next_frame = start
        axes = [0]*6
        filtered = [0.0]*6
        seq = count = 0
        while not args.seconds or time.monotonic()-start < args.seconds:
            if child and child.poll() is not None:
                # CAD exited (or hands off to the 3DEXPERIENCE launcher and restarts):
                # stay alive and attach to the next instance instead of ending the bridge.
                child = None
                path.unlink(missing_ok=True)
                disarm(command[0], env)
            if not args.listen and not child and time.monotonic() >= next_scan:
                next_scan = time.monotonic()+2
                cad = settled_cad()
                if cad and attempts.get(cad, 0) < 3:
                    attempts[cad] = attempts.get(cad, 0)+1
                    register(command[0], env)
                    child = subprocess.Popen(command+['--load-addin'], env=env)
            select.select([lib.spnav_fd()], [], [], max(0, next_frame-time.monotonic()))
            while lib.spnav_poll_event(C.byref(event)):
                if event.type == 1:
                    axes = [getattr(event.motion, n) for n in names]
                    last_motion = time.monotonic()
                    count += 1
                    if args.listen:
                        print('axes', *axes, flush=True)
                elif event.type == 3:
                    print('SpaceMouse connected' if event.motion.x == 0 else 'SpaceMouse disconnected', flush=True)
                elif event.type == 2 and args.listen:
                    print('button', event.button.bnum, 'press' if event.button.press else 'release', flush=True)
            now = time.monotonic()
            if now >= next_frame:
                current = axes if now-last_motion < .15 else [0]*6
                filtered = smooth(filtered, current, now-previous, args.smoothing, args.deadzone)
                if not args.listen and any(filtered):
                    seq += 1
                    motion = values(filtered, now-previous, args.pan, args.rotation, args.zoom, 0, signs)
                    if motion != (0, 0, 1, 0, 0, 0):
                        publish(path, seq, motion)
                previous, next_frame = now, now+1/30
        print(f'Received {count} motion events', flush=True)
        return 0
    except BlockingIOError:
        p.error('A SpaceMouse bridge is already running for this prefix')
    finally:
        if child:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        lib.spnav_close()
        lock.close()
        if child:
            path.unlink(missing_ok=True)
            disarm(command[0], env)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
