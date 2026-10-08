#!/usr/bin/env python3
"""Install this checkout’s SOLIDWORKS launcher in the user application menu."""
import os
from pathlib import Path

def desktop_entry(launcher):
    value = str(launcher)
    if any(c in value for c in '\n\r'):
        raise ValueError('Launcher path must not contain newlines')
    for c in ('\\', '"', '`', '$'):
        value = value.replace(c, '\\'+c)
    value = value.replace('\\', '\\\\').replace('%', '%%')
    return f'''[Desktop Entry]
Type=Application
Name=SOLIDWORKS for Makers
Comment=SOLIDWORKS Design Professional for Makers through Proton
Exec="{value}"
Icon=applications-engineering
Terminal=false
Categories=Graphics;Engineering;
StartupNotify=true
StartupWMClass=sldworks.exe
'''

if __name__ == '__main__':
    launcher = Path(__file__).resolve().with_name('launch_solidworks.sh')
    if not os.access(launcher, os.X_OK):
        raise SystemExit('Make launch_solidworks.sh executable first')
    directory = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'applications'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory/'SM4L-solidworks.desktop'
    target.write_text(desktop_entry(launcher))
    print(target)
