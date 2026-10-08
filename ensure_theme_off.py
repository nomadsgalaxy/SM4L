#!/usr/bin/env python3
"""Keep the prefix's Wine theme off (HKCU ThemeManager ThemeActive = "0").
Themed Button painting hides checkbox and radio labels in the CAD panels; classic painting is the
adopted fix. Wine reads user.reg when its server starts, so the edit only happens while no
wineserver runs for this prefix: launch scripts call this just before they start it.
Usage: ensure_theme_off.py [PREFIX_DIR] [--check]   (default: the SM4L state prefix/pfx; --check never writes)"""
import os, sys
from pathlib import Path

SECTION = r'[Software\\Microsoft\\Windows\\CurrentVersion\\ThemeManager]'

def server_running(prefix):
    want = os.path.realpath(prefix)
    for pid in filter(str.isdigit, os.listdir('/proc')):
        try:
            if Path(f'/proc/{pid}/comm').read_text().strip() != 'wineserver':
                continue
            env = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
        except OSError:
            continue
        for item in env:
            if item.startswith(b'WINEPREFIX=') and os.path.realpath(item[11:].decode()) == want:
                return True
    return False

def fixed_lines(lines):
    """Return (new_lines, state) where state is 'ok', 'changed' or 'added'."""
    out, state, inside = [], None, False
    for line in lines:
        if line.startswith('['):
            if inside and state is None:
                out.append('"ThemeActive"="0"\n'); state = 'added'
            inside = line.startswith(SECTION)
        elif inside and line.startswith('"ThemeActive"='):
            if line.strip() == '"ThemeActive"="0"':
                state = 'ok'
            else:
                line, state = '"ThemeActive"="0"\n', 'changed'
        out.append(line)
    if inside and state is None:
        out.append('"ThemeActive"="0"\n'); state = 'added'
    return out, state

def main(argv):
    check = '--check' in argv
    given = [a for a in argv if not a.startswith('--')]
    # Same default as launch_proton.sh: $SOLIDWORKS_PROTON_STATE or ~/.local/share/solidworks-proton.
    state = os.environ.get('SOLIDWORKS_PROTON_STATE') or os.path.join(
        os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'solidworks-proton')
    prefix = given[0] if given else os.path.join(state, 'prefix', 'pfx')
    reg = Path(prefix)/'user.reg'
    if not reg.exists():
        print('theme guard: no user.reg yet (new prefix); nothing to do')
        return 0
    lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True)
    new, state = fixed_lines(lines)
    if state is None:
        print('theme guard: no ThemeManager section; leaving it to Wine')
        return 0
    if state == 'ok':
        print('theme guard: ThemeActive already "0"')
        return 0
    if check:
        print(f'theme guard: would fix ThemeActive ({state})')
        return 0
    if server_running(prefix):
        print('theme guard: wineserver is running; the fix applies on the next start')
        return 0
    backup = reg.with_name('user.reg.before-theme-guard')
    if not backup.exists():
        backup.write_bytes(reg.read_bytes())
    tmp = reg.with_name('user.reg.theme-guard.tmp')
    tmp.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
    os.replace(tmp, reg)
    print(f'theme guard: set ThemeActive to "0" ({state})')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
