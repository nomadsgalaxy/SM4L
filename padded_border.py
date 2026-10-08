#!/usr/bin/env python3
"""Set or restore HKCU\\Control Panel\\Desktop\\WindowMetrics PaddedBorderWidth in the prefix (offline edit of user.reg).
Windows 10/11 reports a 4 px padded border (SM_CXPADDEDBORDER); Wine reports 0, and SolidWorks' PropertyManager
header layout drifts 4 px per pass when that 4 is missing. The value is in twips: -60 = 4 px at 96 DPI.
set     PaddedBorderWidth = "-60" (remembers the old value)
clear   puts the old value back
status  shows the current value
Run it while NO wineserver runs for the prefix (Wine reads user.reg at server start). Usage: padded_border.py set|clear|status [PREFIX_DIR]"""
import importlib.util, os, sys
from pathlib import Path

SECTION = '[Control Panel\\\\Desktop\\\\WindowMetrics]'
KEY = '"PaddedBorderWidth"='

def load_guard():
    spec = importlib.util.spec_from_file_location('theme_guard', Path(__file__).with_name('ensure_theme_off.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def current(lines):
    inside = False
    for line in lines:
        if line.startswith('['):
            inside = line.startswith(SECTION)
        elif inside and line.startswith(KEY):
            return line.strip()[len(KEY):].strip('"')
    return None

def rewrite(lines, value):
    """Return the lines with PaddedBorderWidth set to `value` (None removes it)."""
    out, inside, done = [], False, False
    for line in lines:
        if line.startswith('['):
            if inside and not done and value is not None:
                out.append(f'{KEY}"{value}"\n'); done = True
            inside = line.startswith(SECTION)
        elif inside and line.startswith(KEY):
            if value is not None:
                out.append(f'{KEY}"{value}"\n')
            done = True
            continue
        out.append(line)
    if inside and not done and value is not None:
        out.append(f'{KEY}"{value}"\n'); done = True
    if not done and value is not None:
        raise SystemExit('No WindowMetrics section in user.reg; leave it to Wine to create it.')
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
    now = current(lines)
    if mode == 'status':
        print('PaddedBorderWidth =', repr(now)); return 0
    if load_guard().server_running(prefix):
        raise SystemExit('A wineserver runs for this prefix; stop it first (Wine reads user.reg at start).')
    sidecar = reg.with_name('user.reg.padded-border-original')
    if mode == 'set':
        if not sidecar.exists():
            sidecar.write_text('' if now is None else now, encoding='utf-8')
        new = rewrite(lines, '-60')
    else:
        if not sidecar.exists():
            print('padded border: nothing to restore'); return 0
        old = sidecar.read_text(encoding='utf-8')
        new = rewrite(lines, old if old != '' else None)
    backup = reg.with_name('user.reg.before-padded-border')
    if not backup.exists():
        backup.write_bytes(reg.read_bytes())
    tmp = reg.with_name('user.reg.padded.tmp')
    tmp.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
    os.replace(tmp, reg)
    if mode == 'clear':
        sidecar.unlink()
    print(f'padded border: {mode} done')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
