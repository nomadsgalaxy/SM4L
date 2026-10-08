#!/usr/bin/env python3
"""Point the things outside the checkout at THIS checkout: the application menu entry and the prefix's WineBrowser value
(HKCU\\Software\\Wine\\WineBrowser Browsers, which Wine's browser handler reads to open the sign-in page in the dedicated
Firefox profile). Run it after moving or cloning the checkout, or let install_units.sh --register-paths do it.
The registry value is set with the prefix's own wine64 when a wineserver is running for the prefix (never starting a
mismatched one), otherwise by editing user.reg directly while no server runs.
Usage: register_paths.py [--check]   (--check prints what would change and writes nothing)"""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SECTION = r'[Software\\Wine\\WineBrowser]'

def browser_value(script):
    """The "Browsers" line for user.reg: Wine stores REG_SZ with backslashes and quotes escaped."""
    text = str(script).replace('\\', '\\\\').replace('"', '\\"')
    return '"Browsers"="%s"\n' % text

def put_before_blanks(out, line):
    at = len(out)
    while at and not out[at - 1].strip():
        at -= 1
    out.insert(at, line)

def set_browser(lines, script):
    """Return (new_lines, changed): sets Browsers under SECTION, creating the section when it is missing."""
    want = browser_value(script)
    out, inside, done = [], False, False
    for line in lines:
        if line.startswith('['):
            if inside and not done:
                put_before_blanks(out, want); done = True
            inside = line.startswith(SECTION)
        elif inside and line.startswith('"Browsers"='):
            line, done = want, True
        out.append(line)
    if inside and not done:
        put_before_blanks(out, want); done = True
    if not done:
        out += ['\n', SECTION + ' 0\n', want]
    return out, out != lines

def server_running(prefix):
    sys.path.insert(0, str(ROOT / 'setup'))
    from ensure_theme_off import server_running as running
    return running(prefix)

def main(argv):
    check = '--check' in argv
    state = Path(os.environ.get('SOLIDWORKS_PROTON_STATE') or Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'solidworks-proton')
    prefix = state / 'prefix' / 'pfx'
    script = ROOT / 'bin' / 'open_windows_firefox.sh'
    if not script.exists():
        sys.exit('register_paths: %s is missing' % script)
    print('menu entry ->', ROOT / 'bin' / 'launch_solidworks.sh')
    print('WineBrowser Browsers ->', script)
    if check:
        return 0
    subprocess.run([sys.executable, str(HERE / 'install_desktop.py')], check=True)
    reg = prefix / 'user.reg'
    if not reg.exists():
        print('No prefix yet (%s): run bin/register_paths.py again once the prefix exists.' % reg)
        return 0
    if server_running(prefix):
        proton = Path(os.environ.get('PROTONPATH') or Path.home() / '.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4')
        env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG='-all')
        subprocess.run([str(proton / 'files/bin/wine64'), 'reg.exe', 'add', r'HKCU\Software\Wine\WineBrowser', '/v', 'Browsers',
                        '/t', 'REG_SZ', '/d', str(script), '/f'], env=env, check=True, stdout=subprocess.DEVNULL)
        print('WineBrowser value set through the running wineserver')
    else:
        lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True)
        new, changed = set_browser(lines, script)
        if changed:
            reg.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
        print('WineBrowser value %s in user.reg (no wineserver was running)' % ('updated' if changed else 'already correct'))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
