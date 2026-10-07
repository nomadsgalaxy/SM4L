"""Build a narrowly scoped CATSysTS import proxy for this verified media release."""
import argparse
import hashlib
from pathlib import Path
import subprocess
from inspect_payload import pe_imports

SOURCE_SHA256='acfb5354bf75164f1e81def14e856aa50004bfb365dea165dcb93c1f6c7b8f35'

def patched_bytes(data):
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Unsupported CATSysTS build; refusing to patch')
    old=b'KERNEL32.dll\0'; new=b'swcompat.dll\0'
    if data.count(old)!=1:
        raise ValueError('Expected one unique KERNEL32 import name')
    result=data.replace(old,new)
    parsed=pe_imports(result)['imports']
    if parsed.get('swcompat.dll')!=pe_imports(data)['imports']['KERNEL32.dll']:
        raise ValueError('Import rewrite did not preserve functions')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output_directory',type=Path)
    a=p.parse_args(); data=a.source.read_bytes(); patched=patched_bytes(data)
    imports=pe_imports(data)['imports']['KERNEL32.dll']
    if any(not isinstance(x,str) for x in imports):
        p.error('Ordinal imports unsupported')
    a.output_directory.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parent
    definition=a.output_directory/'swcompat.def'
    definition.write_text('LIBRARY swcompat\nEXPORTS\n'+''.join('  '+x+'='+('CompatGetProcAddress' if x=='GetProcAddress' else 'KERNEL32.'+x)+'\n' for x in imports))
    obj=a.output_directory/'rtl_name_match.obj'
    subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-c',str(root/'rtl_name_match.c'),'-o',str(obj)],check=True)
    # ponytail: tested Arch x64 Wine import-library paths; parameterize for another distribution.
    subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/machine:x64','/def:'+str(definition),'/out:'+str(a.output_directory/'swcompat.dll'),str(obj),'/usr/lib/wine/x86_64-windows/libkernel32.a','/usr/lib/wine/x86_64-windows/libntdll.a'],check=True)
    (a.output_directory/'CATSysTS.dll').write_bytes(patched)
    print('Built real name-matching compatibility proxy; original source unchanged')

if __name__=='__main__': main()
