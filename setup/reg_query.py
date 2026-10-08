#!/usr/bin/env python3
"""Read one value from a Wine registry file (user.reg or system.reg) without starting Wine.

Usage: reg_query.py FILE KEY VALUE
  KEY    a Windows key path, with single backslashes, e.g. Software\\Wine\\WineBrowser
  VALUE  the value name, e.g. Browsers

Prints a REG_SZ value as text, and a REG_DWORD as 0x<hex>. Exits 1 when the key or value is absent,
so a shell check can use it directly. Wine writes its files with doubled backslashes in key names
and escaped quotes and backslashes in strings; this reader undoes both."""
import re
import sys
from pathlib import Path

SECTION = re.compile(r'^\[(.+?)\](?: \d+)?$')
VALUE = re.compile(r'^"((?:[^"\\]|\\.)*)"=(.*)$')


def _unescape(text):
    return re.sub(r'\\(.)', r'\1', text)


def find_value(text, key, value):
    """Return the value for key/value in a .reg file body, or None."""
    wanted = key.lower()
    in_key = False
    for line in text.splitlines():
        if line.startswith('['):
            m = SECTION.match(line)
            in_key = bool(m) and _unescape(m.group(1)).lower() == wanted
            continue
        if not in_key:
            continue
        m = VALUE.match(line)
        if not m or _unescape(m.group(1)) != value:
            continue
        raw = m.group(2)
        if raw.startswith('dword:'):
            return '0x%x' % int(raw[len('dword:'):], 16)
        if raw.startswith('"') and raw.endswith('"'):
            return _unescape(raw[1:-1])
        return raw
    return None


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    path, key, value = argv
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return 1
    found = find_value(text, key, value)
    if found is None:
        return 1
    print(found)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
