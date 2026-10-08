"""Build and run the host-side checks of the PDM hook release rules (addin/pdm_hook.h); when the connector DLL is installed,
also check the header's size and code bytes against the real file."""
import _paths
import os, re, struct, subprocess, sys, tempfile
from pathlib import Path

root = _paths.ROOT
with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / 'test_pdm_hook'
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-I', str(root / 'addin'), str(root / 'tests' / 'test_pdm_hook.c'), '-o', str(exe)], check=True)
    out = subprocess.run([str(exe)], capture_output=True, text=True)
    sys.stdout.write(out.stdout)
    if out.returncode:
        sys.exit(out.returncode)

header = (root / 'addin' / 'pdm_hook.h').read_text()
size = int(re.search(r'#define PDM_IMAGE_SIZE (0x[0-9a-f]+)u', header).group(1), 16)
rva = int(re.search(r'#define PDM_CODE_RVA (0x[0-9a-f]+)u', header).group(1), 16)
body = re.search(r'pdm_install_code\[PDM_CODE_LENGTH\] = \{([^}]*)\}', header).group(1)
code = bytes(int(x, 16) for x in re.findall(r'0x[0-9a-f]{2}', body))
state = Path(os.environ.get('SOLIDWORKS_PROTON_STATE') or Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'solidworks-proton')
dll = next(iter((state / 'prefix/pfx/drive_c/Program Files/Dassault Systemes').glob('*/win_b64/USWC/PDMSWV6.dll')), None)
if dll is None:
    print('PDMSWV6.dll not installed here: header constants not compared with the file')
    sys.exit(0)
data = dll.read_bytes()
nt = struct.unpack_from('<I', data, 0x3c)[0]
if struct.unpack_from('<I', data, nt + 0x50)[0] != size:
    print('PDMSWV6.dll here is another build (image size differs): the add-in will leave it alone')
    sys.exit(0)
sections = struct.unpack_from('<H', data, nt + 6)[0]
first = nt + 24 + struct.unpack_from('<H', data, nt + 20)[0]
for i in range(sections):
    virtual, va, raw, ptr = struct.unpack_from('<IIII', data, first + 40 * i + 8)
    if va <= rva < va + max(virtual, raw):
        at = rva - va + ptr
        assert data[at:at + len(code)] == code, 'header code bytes differ from the installed PDMSWV6.dll'
        break
else:
    raise AssertionError('install-site RVA not inside any section')
print('header size and install-site bytes match the installed PDMSWV6.dll')
