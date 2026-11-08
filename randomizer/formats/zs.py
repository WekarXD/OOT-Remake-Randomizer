"""Compresión zstd con los diccionarios de TotK (Pack/ZsDic.pack.zs)."""
from compression import zstd

from . import sarc

_DICT_PACK = 'Pack/ZsDic.pack.zs'


class ZsCodec:
    def __init__(self, dict_blobs: dict):
        self._dicts = {k: zstd.ZstdDict(v) for k, v in dict_blobs.items()}

    @classmethod
    def from_archive(cls, nup):
        blobs = sarc.read(zstd.decompress(nup.read(_DICT_PACK)))
        return cls(blobs)

    def _dict_for(self, romfs_path: str):
        if romfs_path.endswith('.rsizetable.zs'):
            return None
        if romfs_path.endswith('.bcett.byml.zs'):
            name = 'bcett.byml.zsdic'
        elif romfs_path.endswith('.pack.zs'):
            name = 'pack.zsdic'
        else:
            name = 'zs.zsdic'
        try:
            return self._dicts[name]
        except KeyError:
            raise ValueError(f'Falta el diccionario zstd "{name}".') from None

    def decompress(self, romfs_path: str, data: bytes) -> bytes:
        d = self._dict_for(romfs_path)
        return zstd.decompress(data, zstd_dict=d) if d else zstd.decompress(data)

    def compress(self, romfs_path: str, data: bytes) -> bytes:
        d = self._dict_for(romfs_path)
        if d:
            return zstd.compress(data, level=19, zstd_dict=d)
        return zstd.compress(data, level=19)
