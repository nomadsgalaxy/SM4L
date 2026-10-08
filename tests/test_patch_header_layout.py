"""Check pinned guard, branch destinations, and unknown-DLL refusal without starting CAD."""
import _paths
import hashlib
from pathlib import Path
import struct
import sys
from patch_header_layout import patched, SHA, ENTRY, CAVE, ORIGINAL
source=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(source).hexdigest()==SHA
result=patched(source)
assert len(result)==len(source)
assert result[64:81]==b"Wine patched DLL\0"
def dest(at,opsize):
 return at+opsize+4+struct.unpack_from('<i',result,at+opsize)[0]
assert dest(ENTRY,1)==CAVE
assert result[CAVE:CAVE+3]==bytes.fromhex('4d85ed')
assert dest(CAVE+3,2)==CAVE+26
assert result[CAVE+9:CAVE+21]==ORIGINAL
assert dest(CAVE+21,1)==ENTRY+12
assert result[CAVE+26:CAVE+29]==bytes.fromhex('4531ff')
assert dest(CAVE+29,1)==0x29c9e
for bad in (b'',source[:-1],result):
 try:patched(bad)
 except ValueError:pass
 else:raise AssertionError('Accepted unsupported/already-patched DLL')
print('Pinned header guard and branch checks passed')
