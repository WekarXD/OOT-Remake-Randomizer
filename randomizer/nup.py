"""Lectura de solo lectura de archivos .nup (ver SPEC.md de NUP)."""
import hashlib
import os
import struct
from compression import zstd

SUPPORTED_UPDATE_VERSION = 131072
SUPPORTED_DISPLAY_VERSION = '1.1.1'  # versión mostrada por el juego para la actualización 131072
TITLE_ID = 0x0400486024DEC000

_NONE = 0xFFFFFFFF


class NupError(Exception):
    """Error al leer un archivo .nup (mensaje en español)."""


class NupArchive:
    def __init__(self, path):
        self._path = os.fspath(path)
        self._f = None
        self.title_id = 0
        self.update_version = None
        self._index = {}
        try:
            self._f = open(self._path, 'rb')
            self._load()
        except NupError:
            self.close()
            raise
        except (OSError, struct.error, IndexError, UnicodeDecodeError) as e:
            self.close()
            raise NupError(f'No se pudo leer el archivo .nup: {e}') from e

    def _load(self):
        f = self._f
        sb = f.read(0x80)
        if len(sb) < 0x80 or sb[:4] != b'NUP\x01':
            raise NupError('El archivo no es un archivo .nup válido: '
                           f'"{self._path}" no es un archivo .nup (firma incorrecta).')
        hsz, _hver, toc_off, toc_size = struct.unpack_from('<HHQQ', sb, 4)
        toc_sha = sb[0x18:0x38]
        blob_off, fsize, pkg_count, flags = struct.unpack_from('<QQII', sb, 0x38)
        actual = os.fstat(f.fileno()).st_size
        if flags != 0 or pkg_count < 1 or hsz < 0x80 or toc_off != hsz:
            raise NupError('Superbloque .nup inválido o con características no soportadas.')
        if fsize != actual or blob_off % 16 or blob_off < toc_off + toc_size or blob_off > actual:
            raise NupError('El archivo .nup está truncado o dañado (tamaños inconsistentes).')
        f.seek(toc_off)
        toc = f.read(toc_size)
        if len(toc) != toc_size or hashlib.sha256(toc).digest() != toc_sha:
            raise NupError('El archivo .nup está dañado: el SHA-256 de la TOC no coincide.')
        _m, pc, dir_count, file_count, sp_off, sp_size = struct.unpack_from('<IIQQQQ', toc, 0)
        if pc != pkg_count:
            raise NupError('El archivo .nup está dañado: número de paquetes inconsistente.')
        pool = toc[sp_off:sp_off + sp_size]
        dir_base = 0x30 + 0x40 * pc
        file_base = dir_base + 0x18 * dir_count
        child_base = file_base + 0x50 * file_count

        def name(off, ln):
            return pool[off:off + ln].decode('utf-8')

        pkgs = []
        for p in range(pc):
            tid, root, _ex, romfs, ver, kind, pflags = struct.unpack_from(
                '<QIIIIBB', toc, 0x30 + 0x40 * p)
            if kind >= 5:
                raise NupError(f'Tipo de paquete .nup desconocido: {kind}.')
            pkgs.append((tid, root, romfs, ver, kind))

        base = next((p for p in pkgs if p[4] == 0), None)
        update = next((p for p in pkgs if p[4] == 1), None)
        target = update or base
        if target is None:
            raise NupError('El archivo .nup no contiene un paquete base ni de actualización.')
        self.title_id = (base or target)[0]
        self.update_version = update[3] if update else None
        if target[2] == _NONE:
            raise NupError('El paquete del .nup no contiene RomFS.')

        index = {}
        stack = [(target[2], '')]
        while stack:
            d, prefix = stack.pop()
            _no, _nl, fc, cc = struct.unpack_from('<IIII', toc, dir_base + 0x18 * d)
            for s in range(fc, fc + cc):
                nid = struct.unpack_from('<I', toc, child_base + 4 * s)[0]
                if nid < dir_count:
                    no, nl = struct.unpack_from('<II', toc, dir_base + 0x18 * nid)
                    stack.append((nid, prefix + name(no, nl) + '/'))
                else:
                    o = file_base + 0x50 * (nid - dir_count)
                    no, nl, size, eo, es = struct.unpack_from('<IIQQQ', toc, o)
                    codec = toc[o + 0x40]
                    if codec not in (0, 1):
                        raise NupError(f'Códec .nup no soportado: {codec}.')
                    if es and eo + es > actual:
                        raise NupError('El archivo .nup está dañado: extensión fuera de rango.')
                    index[prefix + name(no, nl)] = (eo, es, codec)
        self._index = index

    def has(self, romfs_path):
        return romfs_path in self._index

    def read(self, romfs_path):
        try:
            eo, es, codec = self._index[romfs_path]
        except KeyError:
            raise NupError(f'No existe "{romfs_path}" en el archivo .nup.') from None
        if es == 0:
            return b''
        self._f.seek(eo)
        data = self._f.read(es)
        if len(data) != es:
            raise NupError('El archivo .nup está truncado.')
        if codec == 1:
            return zstd.decompress(data)
        return data

    def list(self, prefix=''):
        return sorted(p for p in self._index if p.startswith(prefix))

    def close(self):
        if self._f is not None:
            self._f.close()
            self._f = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
