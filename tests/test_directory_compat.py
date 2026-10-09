"""Independent wildcard contract cases plus exact CATSysTS import rewrite guards."""
import _paths
import ctypes as C
import locale
from pathlib import Path
import subprocess
import tempfile
from build_directory_compat import patched_bytes
from inspect_payload import pe_imports
import sys

locale.setlocale(locale.LC_CTYPE,'C.UTF-8')
class U(C.Structure):
    _fields_=[('Length',C.c_ushort),('MaximumLength',C.c_ushort),('Buffer',C.POINTER(C.c_ushort))]
def u(s):
    b=s.encode('utf-16le'); a=(C.c_ushort*(len(b)//2)).from_buffer_copy(b)
    return U(len(b),len(b),a)
with tempfile.TemporaryDirectory() as d:
    lib=Path(d)/'matcher.so'
    subprocess.run(['cc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(_paths.ROOT/'setup'/'rtl_name_match.c'),'-o',str(lib)],check=True)
    f=C.CDLL(str(lib)).sw_match; f.argtypes=[C.POINTER(U),C.POINTER(U),C.c_ubyte,C.POINTER(C.c_ushort)]; f.restype=C.c_ubyte
    # Expectations include NT empty-name, DOS wildcard and expression-upcase behavior.
    cases=[('', '',0,1),('*','',0,0),('*','a',0,1),('*.dico','x.dico',0,1),('*.dico','x.txt',0,0),
           ('A?C','ABC',0,1),('A?C','AC',0,0),('HE*O','hello',1,1),('he*o','hello',1,0),
           ('<','hello',0,1),('<','hello.txt',0,0),('<.txt','a.b.txt',0,1),('ab<exe','abcd.exe',0,1),('<','a.',0,1),
           ('F>>>"*','F',0,1),('F>>>"*','F.txt',0,1),('F>>>"*','F1234.txt',0,0),
           ('"','.',0,1),('A"','A',0,1),('A"','A.',0,1),('A"','AB',0,0),
           ('É*.DICO','échantillon.dico',1,1),('É*.DICO','échantillon.dico',0,0),
           ('*.*','abc',0,0),('*.','abc.',0,1),('*.','abc',0,0)]
    for e,n,ic,want in cases:
        assert f(C.byref(u(e)),C.byref(u(n)),ic,None)==want,(e,n,ic,want)
    table=(C.c_ushort*65536)(*range(65536)); table[ord('a')]=ord('Z')
    assert f(C.byref(u('Z')),C.byref(u('a')),1,table)==1
    assert f(C.byref(u('A')),C.byref(u('a')),1,table)==0
if len(sys.argv)>1:
    data=Path(sys.argv[1]).read_bytes(); out=patched_bytes(data)
    assert len(out)==len(data)
    before=pe_imports(data)['imports']; after=pe_imports(out)['imports']
    assert after.pop('swcompat.dll')==before.pop('KERNEL32.dll') and before==after
    from apply_directory_compat import apply
    with tempfile.TemporaryDirectory() as d:
        target=Path(d)/'CATSysTS.dll'; target.write_bytes(data)
        apply(target,_paths.ROOT/'setup'/'swcompat.dll')
        assert target.read_bytes()==out
        assert target.with_name('CATSysTS.dll.pre-swcompat').read_bytes()==data
        assert (target.parent/'swcompat.dll').read_bytes()==(_paths.ROOT/'setup'/'swcompat.dll').read_bytes()
        try: apply(target,_paths.ROOT/'setup'/'swcompat.dll')
        except ValueError: pass
        else: raise AssertionError('Patched an already changed DLL')
    with tempfile.TemporaryDirectory() as d:
        target=Path(d)/'CATSysTS.dll'; target.write_bytes(data)
        (target.parent/'swcompat.dll').write_bytes(b'unrelated existing DLL')
        try: apply(target,_paths.ROOT/'setup'/'swcompat.dll')
        except ValueError: pass
        else: raise AssertionError('Overwrote unrelated proxy')
        assert target.read_bytes()==data
        assert not target.with_name('CATSysTS.dll.pre-swcompat').exists()
    for bad in (b'',data[:-1],data[:100]+b'!'+data[101:]):
        try: patched_bytes(bad)
        except ValueError: pass
        else: raise AssertionError('Accepted altered source')
print('Name matching, Unicode/custom table and import rewrite checks passed')
