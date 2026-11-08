"""Minimal read-only NUP TOC lister (stdlib only), written from SPEC.md.
Usage: python nuplist.py game.nup out.tsv
Writes: path<TAB>size<TAB>extent_offset<TAB>extent_size<TAB>codec
"""
import struct, sys, hashlib

def main(nup, out):
    with open(nup, 'rb') as f:
        sb = f.read(0x80)
        assert sb[:4] == b'NUP\x01', 'bad magic'
        hsz, hver, toc_off, toc_size = struct.unpack_from('<HHQQ', sb, 4)
        toc_sha = sb[0x18:0x38]
        blob_off, fsize, pkg_count, flags = struct.unpack_from('<QQII', sb, 0x38)
        f.seek(toc_off)
        toc = f.read(toc_size)
    assert hashlib.sha256(toc).digest() == toc_sha, 'TOC hash mismatch'
    magic, pc, dir_count, file_count, sp_off, sp_size = struct.unpack_from('<IIQQQQ', toc, 0)
    pool = toc[sp_off:sp_off + sp_size]
    pk_base = 0x30
    dir_base = pk_base + 0x40 * pc
    file_base = dir_base + 0x18 * dir_count
    child_base = file_base + 0x50 * file_count

    def name(off, ln):
        return pool[off:off + ln].decode('utf-8')

    def dirrec(i):
        return struct.unpack_from('<IIII', toc, dir_base + 0x18 * i)

    def filerec(i):
        o = file_base + 0x50 * i
        no, nl, size, eo, es = struct.unpack_from('<IIQQQ', toc, o)
        codec = toc[o + 0x40]
        return name(no, nl), size, eo, es, codec

    pkgs = []
    for p in range(pc):
        tid, root, exefs, romfs, ver, kind, pflags = struct.unpack_from('<QIIIIBB', toc, pk_base + 0x40 * p)
        pkgs.append((tid, root, exefs, romfs, ver, kind, pflags))
        print(f'package {p}: title {tid:016X} ver {ver} kind {kind} flags {pflags}', file=sys.stderr)
    print(f'dirs {dir_count} files {file_count}', file=sys.stderr)

    with open(out, 'w', encoding='utf-8', newline='\n') as w:
        for p, (tid, root, *_rest) in enumerate(pkgs):
            stack = [(root, f'p{p}')]
            while stack:
                d, path = stack.pop()
                no, nl, fc, cc = dirrec(d)
                for s in range(fc, fc + cc):
                    nid = struct.unpack_from('<I', toc, child_base + 4 * s)[0]
                    if nid < dir_count:
                        dn = dirrec(nid)
                        stack.append((nid, path + '/' + name(dn[0], dn[1])))
                    else:
                        n, size, eo, es, codec = filerec(nid - dir_count)
                        w.write(f'{path}/{n}\t{size}\t{eo}\t{es}\t{codec}\n')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
