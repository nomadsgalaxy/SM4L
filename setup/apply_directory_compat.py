"""Apply the verified directory-matching proxy to an isolated CATSysTS installation."""
import argparse
import hashlib
from pathlib import Path
import os
import tempfile
import time
from build_directory_compat import patched_bytes, SOURCE_SHA256
from inspect_payload import pe_imports


def apply(target, shim):
    data=target.read_bytes()
    out=patched_bytes(data)
    shim_data=shim.read_bytes()
    # ponytail: x64 PE proxy built here; broader architecture/runtime support needs another build.
    if pe_imports(shim_data)['machine']!='0x8664':
        raise ValueError('Compatibility proxy must be an x64 Windows PE DLL')
    installed_shim=target.parent/'swcompat.dll'
    if installed_shim.exists() and installed_shim.read_bytes()!=shim_data:
        raise ValueError('Existing swcompat.dll differs; refusing to replace it')
    backup=target.with_name(target.name+'.pre-swcompat')
    if backup.exists():
        if backup.read_bytes()!=data: raise ValueError('Existing backup differs from original')
    else:
        with backup.open('xb') as f: f.write(data)
    installed_shim.write_bytes(shim_data)
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as f:
        temporary=Path(f.name); f.write(out)
    try:
        temporary.chmod(target.stat().st_mode)
        os.replace(temporary,target)
    finally:
        temporary.unlink(missing_ok=True)
    print('Applied real directory matcher; original backed up at '+str(backup))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',type=Path)
    p.add_argument('--shim',type=Path,default=Path(__file__).with_name('swcompat.dll'))
    p.add_argument('--watch-for-recopy',action='store_true',help='Wait up to 15 minutes for the verified original DLL during vendor Restart installation')
    a=p.parse_args()
    if a.watch_for_recopy:
        for _ in range(900):
            try:
                if hashlib.sha256(a.target.read_bytes()).hexdigest()==SOURCE_SHA256: break
            except FileNotFoundError: pass
            time.sleep(1)
        else: p.error('No verified original DLL appeared within 15 minutes')
    apply(a.target,a.shim)


if __name__=='__main__': main()
