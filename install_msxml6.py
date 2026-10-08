#!/usr/bin/env python3
"""Give SOLIDWORKS Microsoft's msxml6.dll (and only SOLIDWORKS), so the 3MF export stops crashing.
Wine's built-in msxml3 (which backs msxml6) over-releases a document when SOLIDWORKS moves nodes between
documents, then frees it and crashes in get_xml. Microsoft's msxml6 does not have that bug and accepts every
property SOLIDWORKS sets (msxml3 does not, so native msxml3 breaks CAD at startup).
What it does, with the prefix stopped:
  1. checks the KB2957482 amd64 package against a pinned SHA256 and extracts the four DLLs (needs 7z),
  2. backs up the prefix's two built-in msxml6.dll stubs and user.reg (once, in <state>/prefix/msxml6-backup),
  3. copies msxml6.dll and msxml6r.dll into system32 (x64) and syswow64 (x86),
  4. adds "msxml6"="native,builtin" under HKCU\\Software\\Wine\\AppDefaults\\sldworks.exe\\DllOverrides.
Other programs keep Wine's built-in msxml6 because the override is scoped to sldworks.exe.
Usage: install_msxml6.py [PREFIX_DIR] [--package FILE] [--check | --rollback]
  PREFIX_DIR  default: the SM4L state prefix/pfx (same default as launch_proton.sh)
  --package   default: the file winetricks caches, ~/.cache/winetricks/msxml6/msxml6-KB2957482-enu-amd64.exe
  --check     report what is installed, change nothing        --rollback  undo it (restores the backed-up stubs)"""
import hashlib, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

PACKAGE = 'msxml6-KB2957482-enu-amd64.exe'
PACKAGE_SHA256 = '260cd870851ffc3c6d10b71691f134e20d8d03ac26073bb36951eacb7aa85897'
# (extracted name in the .msi, folder in drive_c/windows, SHA256 of the file)
FILES = [
    ('msxml6.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB', 'system32', 'msxml6.dll',
     '6fb5aead277001403cd01178346253455cdb9926b69f12ee99764ae358d7b21b'),
    ('msxml6r.dll.1ECC0691_D2EB_4A33_9CBF_5487E5CB17DB', 'system32', 'msxml6r.dll',
     '6e476a37fcff8ceab3ea9d08b381cc42238b00ad50b0fd05250b621c4ecdbce2'),
    ('msxml6.dll.86F857F6_A743_463D_B2FE_98CB5F727E09', 'syswow64', 'msxml6.dll',
     '66fb552089d28797ed74afbff5ab2c739828cf9abb10579a6641d5bd51cdec7b'),
    ('msxml6r.dll.86F857F6_A743_463D_B2FE_98CB5F727E09', 'syswow64', 'msxml6r.dll',
     'c4c3e734abbf54424f878457d93e4981f0ef19cfa974aeeacddfa916a508b185'),
]
SECTION = r'[Software\\Wine\\AppDefaults\\sldworks.exe\\DllOverrides]'
VALUE = '"msxml6"="native,builtin"'

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

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

def put_before_blanks(out, line):
    """Append line after the last non-blank line of out (keeps the blank gap before the next section)."""
    at = len(out)
    while at and not out[at - 1].strip():
        at -= 1
    out.insert(at, line)

def add_override(lines):
    """Return (new_lines, changed). Sets VALUE under SECTION, creating the section when it is missing."""
    out, inside, added = [], False, False
    for line in lines:
        if line.startswith('['):
            if inside and not added:
                put_before_blanks(out, VALUE + '\n'); added = True
            inside = line.startswith(SECTION)
        elif inside and line.startswith('"msxml6"='):
            line, added = VALUE + '\n', True
        out.append(line)
    if inside and not added:
        put_before_blanks(out, VALUE + '\n'); added = True
    if not added:
        out += ['\n', f'{SECTION} {int(time.time())}\n', VALUE + '\n']
    return out, out != lines

def remove_override(lines):
    """Return (new_lines, changed): drops the msxml6 line under SECTION and nothing else."""
    out, inside, changed = [], False, False
    for line in lines:
        if line.startswith('['):
            inside = line.startswith(SECTION)
        elif inside and line.startswith('"msxml6"='):
            changed = True
            continue
        out.append(line)
    return out, changed

def has_override(lines):
    return remove_override(lines)[1]

def extract(package, dest):
    """7z the package (exe -> msi -> files) into dest; return dest."""
    sevenz = shutil.which('7z') or shutil.which('7za')
    if not sevenz:
        sys.exit('install_msxml6: 7z is needed to unpack the package (install p7zip)')
    for archive in (package, Path(dest) / 'msxml6.msi'):
        subprocess.run([sevenz, 'x', '-y', f'-o{dest}', str(archive)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Path(dest)

def state_of(prefix):
    win = Path(prefix) / 'drive_c' / 'windows'
    dlls = all((win / d / n).exists() and sha256(win / d / n) == h for _, d, n, h in FILES)
    reg = Path(prefix) / 'user.reg'
    lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True) if reg.exists() else []
    return dlls, has_override(lines)

def backup_dir(prefix):
    return Path(prefix).parent / 'msxml6-backup'

def install(prefix, package):
    prefix = Path(prefix); win = prefix / 'drive_c' / 'windows'
    if (dlls_ok := state_of(prefix))[0] and dlls_ok[1]:
        print('msxml6: already installed for sldworks.exe'); return 0
    if not package.exists():
        sys.exit(f'install_msxml6: package not found: {package}\n'
                 f'  expected {PACKAGE} (SHA256 {PACKAGE_SHA256}); winetricks caches it when you run "winetricks msxml6"')
    if sha256(package) != PACKAGE_SHA256:
        sys.exit('install_msxml6: package SHA256 does not match the pinned KB2957482 amd64 build; not installing')
    with tempfile.TemporaryDirectory() as tmp:
        src = extract(package, tmp)
        for name, _, _, want in FILES:
            if not (src / name).exists() or sha256(src / name) != want:
                sys.exit(f'install_msxml6: extracted {name} is missing or has an unexpected hash; not installing')
        backup = backup_dir(prefix)
        if not backup.exists():
            backup.mkdir()
            shutil.copy2(prefix / 'user.reg', backup / 'user.reg')
            for folder in ('system32', 'syswow64'):
                shutil.copy2(win / folder / 'msxml6.dll', backup / f'{folder}-msxml6.dll')
            print(f'msxml6: backed up to {backup}')
        for name, folder, target, _ in FILES:
            shutil.copy2(src / name, win / folder / target)
    reg = prefix / 'user.reg'
    lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True)
    new, changed = add_override(lines)
    if changed:
        reg.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
    print('msxml6: installed Microsoft msxml6 for sldworks.exe only')
    return 0

def rollback(prefix):
    prefix = Path(prefix); win = prefix / 'drive_c' / 'windows'; backup = backup_dir(prefix)
    for folder in ('system32', 'syswow64'):
        saved = backup / f'{folder}-msxml6.dll'
        if not saved.exists():
            sys.exit(f'install_msxml6: no backup of {folder}/msxml6.dll in {backup}; not rolling back')
    for folder in ('system32', 'syswow64'):
        shutil.copy2(backup / f'{folder}-msxml6.dll', win / folder / 'msxml6.dll')
    for _, folder, target, want in FILES:
        path = win / folder / target
        if target == 'msxml6r.dll' and path.exists() and sha256(path) == want:
            path.unlink()
    reg = prefix / 'user.reg'
    lines = reg.read_text(encoding='utf-8', errors='surrogateescape').splitlines(keepends=True)
    new, changed = remove_override(lines)
    if changed:
        reg.write_text(''.join(new), encoding='utf-8', errors='surrogateescape')
    print('msxml6: rolled back to the built-in stubs')
    return 0

def main(argv):
    args = list(argv)
    package = Path(os.path.expanduser(f'~/.cache/winetricks/msxml6/{PACKAGE}'))
    if '--package' in args:
        i = args.index('--package'); package = Path(args[i + 1]); del args[i:i + 2]
    flags = {a for a in args if a.startswith('--')}
    given = [a for a in args if not a.startswith('--')]
    state = os.environ.get('SOLIDWORKS_PROTON_STATE') or os.path.join(
        os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'solidworks-proton')
    prefix = given[0] if given else os.path.join(state, 'prefix', 'pfx')
    if not (Path(prefix) / 'user.reg').exists():
        sys.exit(f'install_msxml6: no user.reg in {prefix}; start the prefix once first')
    if '--check' in flags:
        dlls, reg = state_of(prefix)
        print(f'msxml6 files installed: {dlls}; sldworks.exe override set: {reg}')
        return 0
    if server_running(prefix):
        sys.exit('install_msxml6: a wineserver is running for this prefix; stop it first (wineserver -k)')
    return rollback(prefix) if '--rollback' in flags else install(prefix, package)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
