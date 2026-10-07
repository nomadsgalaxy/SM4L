"""Pinned, prefix-local Wine HDM_LAYOUT null guard; preserve the original DLL."""
import hashlib
import struct
from pathlib import Path
SHA = 'd0616fbdb1649047ac7f0fea3a55f8ab70b33b4c0703c056a6706c43c0cf1676'
ENTRY = 0x2ac1e
CAVE = 0xb1af0
ORIGINAL = bytes.fromhex('498b450848c7400800000000')
def jump(op, at, target):
    return op + struct.pack('<i', target - at - len(op) - 4)
def patched(original):
    if hashlib.sha256(original).hexdigest() != SHA:
        raise ValueError('Unsupported Wine common-controls DLL')
    b = bytearray(original)
    # This pinned PE maps .text RVA and raw offset identically.
    pe = struct.unpack_from('<I', b, 60)[0]
    section = pe + 24 + struct.unpack_from('<H', b, pe + 20)[0]
    assert b[section:section+8] == b'.text\0\0\0'
    assert struct.unpack_from('<IIII', b, section+8) == (0xb0af0, 0x1000, 0xb1000, 0x1000)
    assert b[ENTRY:ENTRY+12] == ORIGINAL
    assert b[CAVE:CAVE+64] == bytes(64)
    code = b'\x4d\x85\xed'  # test r13,r13 (HDLAYOUT pointer)
    code += jump(b'\x0f\x84', CAVE+3, CAVE+26)
    code += ORIGINAL
    code += jump(b'\xe9', CAVE+21, ENTRY+12)
    code += b'\x45\x31\xff'  # failure result = FALSE
    code += jump(b'\xe9', CAVE+29, 0x29c9e)  # existing epilogue
    b[CAVE:CAVE+len(code)] = code
    b[ENTRY:ENTRY+12] = jump(b'\xe9', ENTRY, CAVE) + b'\x90'*7
    struct.pack_into('<I', b, section+8, 0xb0af0+len(code))
    assert b[64:81] == b"Wine builtin DLL\0"
    b[64:81] = b"Wine patched DLL\0"  # load this PE instead of redirecting to shared Proton
    return bytes(b)
if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dll',type=Path);a=p.parse_args()
    original=a.dll.read_bytes();result=patched(original)
    backup=a.dll.with_name('comctl32.before-header-guard.dll')
    if backup.exists():
        if backup.read_bytes()!=original:raise ValueError('Backup mismatch')
    else:
        with backup.open('xb') as f:f.write(original)
    a.dll.write_bytes(result)
    assert a.dll.read_bytes()==result
    print('Applied prefix-local guard; original SHA256:',SHA)
