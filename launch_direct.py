#!/usr/bin/env python3
"""Start SWXDesktopLauncher straight from this host (no browser Open), using the per-user
3DEXPERIENCE values the launcher already saved in the prefix registry.
It never prints, logs or stores a value: --dry-run shows only the argument names and lengths.
Experiment: the per-click transient auth URL is NOT passed. Whether the launcher then logs in
from its saved session is exactly what this tests, so it needs Anthony and a saved CAD state."""
import argparse, os, subprocess, sys
from pathlib import Path

KEY = r'HKCU\Software\Dassault Systemes\SOLIDWORKSPDM\Servers\3DEXPERIENCE'
LAUNCHER = r'C:\Program Files\Dassault Systemes\SOLIDWORKS 3DEXPERIENCE R2026x\win_b64\code\bin\SWXDesktopLauncher.exe'

def alive():
    """Names of processes whose presence would make a direct launch collide."""
    found = []
    for comm in ('sldworks.exe', 'SWXDesktopLaunc', 'CATSTART.exe'):
        if subprocess.run(['pgrep', '-x', comm], capture_output=True).returncode == 0:
            found.append(comm)
    return found

def registry(wine, env):
    out = subprocess.run([wine, 'reg.exe', 'query', KEY], env=env, capture_output=True, text=True, timeout=60).stdout
    values = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[1].startswith('REG_') and not line.startswith('HKEY'):
            values[parts[0]] = parts[2].strip()
    return values

def build_args(v):
    need = ('SpaceURL', 'MyAppsURL', 'Tenant', 'UserName', 'CAS', 'PassportURL', 'RegistryURL')
    missing = [k for k in need if not v.get(k)]
    if missing:
        raise SystemExit('Registry values missing (sign in once through the browser first): ' + ', '.join(missing))
    space = v['SpaceURL'].rstrip('/')
    if not space.endswith('/enovia'):
        space += '/enovia'
    cas = v['CAS'] if v['CAS'].startswith('CASTGC=') else 'CASTGC=' + v['CAS']
    return [f'-Url={space}', '-Prfctx', '--AppName=SWXCSWK_AP', f'-MyAppsURL={v["MyAppsURL"]}',
            f'-tenant={v["Tenant"].upper()}', f'-username={v["UserName"]}', '-monoapp', f'-Cas={cas}',
            f'-PassportURL={v["PassportURL"]}', '-RegistryUrl', v['RegistryURL'],
            f'-3DRegistryURL={v["RegistryURL"]}', '-PLMCSAClient=True']

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run', action='store_true', help='Check refusals and show argument names and lengths only')
    args = p.parse_args()
    busy = alive()
    if busy:
        raise SystemExit('Refusing to start: already running: ' + ', '.join(busy))
    state = Path(os.environ.get('SOLIDWORKS_PROTON_STATE', Path.home()/'.local/share/solidworks-proton'))
    wine = os.environ.get('PROTONPATH', str(Path.home()/'.local/share/Steam/compatibilitytools.d/UMU-Proton-10.0-4'))+'/files/bin/wine64'
    env = dict(os.environ, WINEPREFIX=str(state/'prefix/pfx'), WINEDEBUG='-all', WINEFSYNC='0', WINEESYNC='0')
    launch_args = build_args(registry(wine, env))
    if args.dry_run:
        for a in launch_args:
            print(f'{a.split("=", 1)[0] if a.startswith("-") else "<value>"} ({len(a)} chars)')
        return 0
    exe = state/'prefix/pfx/drive_c'/Path(*LAUNCHER[3:].split('\\'))
    launch = Path(__file__).with_name('launch_proton.sh')
    here = dict(os.environ, SOLIDWORKS_PROTON_STATE=str(state), SM4L_SPACEMOUSE='0', SM4L_UI_COMPAT='0')
    here.setdefault('PROTONPATH', str(Path(wine).parents[2]))
    return subprocess.call([str(launch), str(exe), *launch_args], env=here)

if __name__ == '__main__':
    raise SystemExit(main())
