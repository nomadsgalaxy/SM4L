"""Inspect indexed SolidWorks payloads without running the Windows installer."""
import argparse
import ctypes as C
import ctypes.util
import fnmatch
import json
from pathlib import Path
import sqlite3
import struct
import zipfile


class Buffer(C.Structure):
    _fields_ = [('ptr', C.c_void_p), ('size', C.c_size_t), ('pos', C.c_size_t)]


def decode_frame(stream, size):
    lib = C.CDLL(ctypes.util.find_library('zstd'))
    lib.ZSTD_createDStream.restype = C.c_void_p
    for name in ('ZSTD_initDStream', 'ZSTD_freeDStream'):
        getattr(lib, name).argtypes = [C.c_void_p]
    lib.ZSTD_decompressStream.argtypes = [C.c_void_p, C.POINTER(Buffer), C.POINTER(Buffer)]
    lib.ZSTD_decompressStream.restype = C.c_size_t
    lib.ZSTD_isError.argtypes = [C.c_size_t]
    ctx = lib.ZSTD_createDStream()
    if not ctx:
        raise MemoryError('Could not allocate Zstandard decoder')
    # ponytail: whole payload in memory; stream to disk for multi-GB payloads.
    parts, total, remaining = [], 0, 1
    try:
        lib.ZSTD_initDStream(ctx)
        while remaining:
            raw = stream.read(1024 * 1024)
            if not raw:
                raise ValueError('Truncated payload')
            src = C.create_string_buffer(raw)
            inp = Buffer(C.cast(src, C.c_void_p), len(raw), 0)
            while inp.pos < inp.size and remaining:
                dst = C.create_string_buffer(1024 * 1024)
                out = Buffer(C.cast(dst, C.c_void_p), len(dst), 0)
                remaining = lib.ZSTD_decompressStream(ctx, C.byref(out), C.byref(inp))
                if lib.ZSTD_isError(remaining):
                    raise ValueError('Zstandard decoding failed')
                total += out.pos
                if total > size:
                    raise ValueError('Payload exceeds indexed size')
                parts.append(dst.raw[:out.pos])
        if total != size:
            raise ValueError(f'Payload size mismatch: {total} != {size}')
        return b''.join(parts)
    finally:
        lib.ZSTD_freeDStream(ctx)


def pe_imports(data):
    if data[:2] != b'MZ':
        raise ValueError('Not a PE binary')
    pe = struct.unpack_from('<I', data, 60)[0]
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('Invalid PE signature')
    machine, count = struct.unpack_from('<HH', data, pe + 4)
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from('<H', data, optional)[0]
    if magic not in (0x10b, 0x20b):
        raise ValueError('Unsupported PE optional header')
    directories = optional + (112 if magic == 0x20b else 96)
    sections = [struct.unpack_from('<8sIIII', data, optional + optional_size + i * 40)
                for i in range(count)]

    def offset(rva):
        for _, virtual_size, address, raw_size, raw_offset in sections:
            if address <= rva < address + max(virtual_size, raw_size):
                result = raw_offset + rva - address
                if result >= len(data):
                    break
                return result
        raise ValueError(f'Unmapped RVA: {rva:x}')

    imports = {}
    rva, _ = struct.unpack_from('<II', data, directories + 8)
    if rva:
        pos = offset(rva)
        while any(data[pos:pos + 20]):
            original, _, _, name, first = struct.unpack_from('<IIIII', data, pos)
            start = offset(name)
            dll = data[start:data.index(b'\0', start)].decode('ascii')
            thunk, entries = offset(original or first), []
            width = 8 if magic == 0x20b else 4
            while True:
                value = struct.unpack_from('<Q' if width == 8 else '<I', data, thunk)[0]
                if not value:
                    break
                if value & (1 << (width * 8 - 1)):
                    entries.append({'ordinal': value & 0xffff})
                else:
                    start = offset(value) + 2
                    entries.append(data[start:data.index(b'\0', start)].decode('ascii'))
                thunk += width
            imports[dll] = entries
            pos += 20
    return {'machine': hex(machine), 'clr_directory': struct.unpack_from('<II', data, directories + 14 * 8),
            'imports': imports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('pattern', help='Glob matched against the indexed destination path, using / separators')
    parser.add_argument('--output', type=Path, help='Save one decoded payload to this exact file')
    args = parser.parse_args()
    with zipfile.ZipFile(args.archive) as archive:
        root = archive.namelist()[0].split('/')[0]
        db = sqlite3.connect(':memory:')
        db.deserialize(archive.read(root + '/1/media.db'))
        rows = db.execute('SELECT f.dest,f.size,f.offset,x.name,x.volume FROM Files f JOIN Features x USING(featureid)').fetchall()
        rows = [r for r in rows if fnmatch.fnmatchcase(r[0].replace('\\', '/'), args.pattern)]
        if not rows or (args.output and len(rows) != 1):
            raise ValueError(f'Matched {len(rows)} payloads; output requires exactly one')
        results = []
        for dest, size, position, feature, volume in rows:
            package = f'{root}/{volume}/CAFS/' + feature.replace('\\', '/') + '.dsa'
            with archive.open(package) as stream:
                stream.seek(position)
                data = decode_frame(stream, size)
            if args.output:
                with args.output.open('xb') as output:
                    output.write(data)
            result = {'path': dest, 'size': size}
            if data[:2] == b'MZ':
                result.update(pe_imports(data))
            results.append(result)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
