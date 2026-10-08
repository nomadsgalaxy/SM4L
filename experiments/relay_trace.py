#!/usr/bin/env python3
"""Set or clear the filtered +relay trace values in the prefix registry (offline edit of user.reg).
set    adds HKCU\\Software\\Wine\\Debug RelayInclude and RelayFromExclude
clear  removes them again
status shows what is set
Run it while NO wineserver runs for the prefix (Wine reads user.reg at server start), then start the
prefix with WINEDEBUG=+relay (for example: WINEDEBUG=+relay bin/launch_solidworks.sh)."""
import importlib.util, os, sys
from pathlib import Path

INCLUDE = ';'.join(['uxtheme.' + n for n in (
    'OpenThemeData', 'OpenThemeDataEx', 'CloseThemeData', 'GetThemePartSize', 'GetThemeTextExtent',
    'DrawThemeText', 'DrawThemeTextEx', 'DrawThemeBackground', 'GetThemeMetric', 'GetThemeInt',
    'GetThemeFont', 'GetThemeColor', 'GetThemeBool', 'IsThemePartDefined', 'GetThemeSysSize',
    'GetThemeSysFont', 'GetThemeBackgroundContentRect', 'GetThemeBackgroundExtent',
    'GetThemeMargins', 'GetThemePosition', 'GetThemeRect')] + [
    'user32.SetWindowPos', 'user32.DeferWindowPos', 'user32.MoveWindow', 'user32.DrawTextW',
    'gdi32.GetTextExtentPoint32W'])
FROM_EXCLUDE = 'ntdll;kernelbase;kernel32;win32u;user32;gdi32;comctl32;msvcrt;ucrtbase;combase;ole32;rpcrt4;wined3d;dxvk;vulkan-1'
SECTION = '[Software\\\\Wine\\\\Debug]'
NAMES = ('"RelayInclude"=', '"RelayFromExclude"=')

def load_guard():
    spec = importlib.util.spec_from_file_location('theme_guard', Path(__file__).resolve().parents[1]/'setup'/'ensure_theme_off.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def edit(lines, mode, original):
    """`original` is the prefix's own RelayFromExclude line (Proton ships one); set replaces it, clear restores it."""
    wanted = [f'"RelayInclude"="{INCLUDE}"\n', f'"RelayFromExclude"="{FROM_EXCLUDE}"\n'] if mode == 'set' else (
        [original] if original else [])
    out, inside, done = [], False, False
    for line in lines:
        if line.startswith('['):
            if inside and not done:
                out += wanted; done = True
            inside = line.startswith(SECTION)
        elif inside and line.startswith(NAMES):
            if not done:
                out += wanted; done = True
            continue
        out.append(line)
    if not done:
        if inside:
            out += wanted
        elif wanted:
            out += ['\n', SECTION + ' 1\n'] + wanted
    return out

def main(argv):
    mode = argv[0] if argv and argv[0] in ('set', 'clear', 'status') else None
    if not mode:
        raise SystemExit(__doc__)
    state = os.environ.get('SOLIDWORKS_PROTON_STATE') or os.path.join(
        os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'solidworks-proton')
    prefix = argv[1] if len(argv) > 1 else os.path.join(state, 'prefix', 'pfx')
    reg = Path(prefix)/'user.reg'
    lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True)
    present = [l.strip()[:40] for l in lines if l.startswith(NAMES)]
    if mode == 'status':
        print('relay values:', present or 'none'); return 0
    if load_guard().server_running(prefix):
        raise SystemExit('A wineserver runs for this prefix; stop it first (Wine reads user.reg at start).')
    sidecar = reg.with_name('user.reg.relay-original')
    if mode == 'set' and not sidecar.exists():
        keep = [l for l in lines if l.startswith('"RelayFromExclude"=')]
        sidecar.write_text(keep[0] if keep else '', encoding='utf-8')
    original = sidecar.read_text(encoding='utf-8') if sidecar.exists() else ''
    new = edit(lines, mode, original or None)
    backup = reg.with_name('user.reg.before-relay-trace')
    if not backup.exists():
        backup.write_bytes(reg.read_bytes())
    tmp = reg.with_name('user.reg.relay.tmp')
    tmp.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
    os.replace(tmp, reg)
    if mode == 'clear' and sidecar.exists():
        sidecar.unlink()
    print(f'relay trace: {mode} done')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
