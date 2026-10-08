"""Checks for setup/reg_query.py against fixture snippets shaped like Wine's user.reg and system.reg."""
import subprocess
import sys
from pathlib import Path

from _paths import ROOT  # noqa: F401  (puts setup/ on sys.path and sets ROOT)
import reg_query

USER_REG = r'''WINE REGISTRY Version 2
;; All keys relative to \\User\\S-1-5-21-1

[Software\\Microsoft\\Windows\\CurrentVersion\\ThemeManager] 1791468487
#time=1dd572e71c3bd62
"ColorName"="Blue"
"DllName"="C:\\\\windows\\\\resources\\\\themes\\\\light\\\\light.msstyles"
"ThemeActive"="0"

[Software\\Wine\\WineBrowser] 1791339168
"Browsers"="/home/user/checkout/bin/open_windows_firefox.sh"
'''

SYSTEM_REG = r'''WINE REGISTRY Version 2

[System\\ControlSet001\\Services\\3DEXPERIENCELauncher] 1791332908
#time=1dd572e71c3bd62
"DisplayName"="3DEXPERIENCE Launcher"
"Type"=dword:00000110
"Start"=dword:00000003

[System\\CurrentControlSet\\Services\\Other] 1791332908
"Type"=dword:00000010
'''


def check(text, key, value, expected):
    got = reg_query.find_value(text, key, value)
    assert got == expected, (key, value, got, expected)


# The theme value: a REG_SZ with the escaped quote-free string "0".
check(USER_REG, r'Software\Microsoft\Windows\CurrentVersion\ThemeManager', 'ThemeActive', '0')
# A string that contains escaped backslashes comes back unescaped.
check(USER_REG, r'Software\Microsoft\Windows\CurrentVersion\ThemeManager', 'DllName', r'C:\\windows\\resources\\themes\\light\\light.msstyles')
# The browser handler path, a plain string.
check(USER_REG, r'Software\Wine\WineBrowser', 'Browsers', '/home/user/checkout/bin/open_windows_firefox.sh')
# The service type is a DWORD, reported as hex so the shell can compare it with 0x110.
check(SYSTEM_REG, r'System\ControlSet001\Services\3DEXPERIENCELauncher', 'Type', '0x110')
# Key names are compared without regard to case, as Windows does.
check(SYSTEM_REG, r'system\controlset001\services\3dexperiencelauncher', 'Type', '0x110')
# A value under a different key is not picked up by mistake.
check(SYSTEM_REG, r'System\CurrentControlSet\Services\Other', 'Type', '0x10')
# A key or value that isn't in the file gives nothing.
check(USER_REG, r'Software\Wine\WineBrowser', 'Missing', None)
check(USER_REG, r'Software\Nope', 'Browsers', None)
# A value name that only appears under another section is not matched.
check(USER_REG, r'Software\Wine\WineBrowser', 'ThemeActive', None)

# The command-line interface: exit 0 with the value, exit 1 when it's missing, exit 1 for a missing file.
tmp = Path(sys.argv[0]).resolve().parent / '_reg_query_fixture'
tmp.mkdir(exist_ok=True)
user = tmp / 'user.reg'
user.write_text(USER_REG, encoding='utf-8')
cli = [sys.executable, '-B', str(ROOT / 'setup' / 'reg_query.py')]
ok = subprocess.run(cli + [str(user), r'Software\Microsoft\Windows\CurrentVersion\ThemeManager', 'ThemeActive'], capture_output=True, text=True)
assert ok.returncode == 0 and ok.stdout.strip() == '0', ok
missing = subprocess.run(cli + [str(user), r'Software\Wine\WineBrowser', 'Nope'], capture_output=True, text=True)
assert missing.returncode == 1, missing
nofile = subprocess.run(cli + [str(tmp / 'absent.reg'), r'Software\Wine\WineBrowser', 'Browsers'], capture_output=True, text=True)
assert nofile.returncode == 1, nofile
user.unlink()
tmp.rmdir()
print('reg_query checks passed')
