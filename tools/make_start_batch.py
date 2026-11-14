"""Test batch 21: start-preset spike. On leaving Link's house for the first time
you get the Fairy Ocarina and are teleported to Hyrule Field by the Lost Woods bridge.
Usage: python -I tools/make_start_batch.py <nup> <out_mod_dir>
Only reads the .nup; writes <out_mod_dir>/romfs/... (built in <out_mod_dir>.tmp, then
swapped in).
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from randomizer.formats.rstb import Rstb  # noqa: E402
from randomizer.formats.zs import ZsCodec  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.patch import RSTB_PATH  # noqa: E402
from randomizer.formats.bfevfl import EventFlow  # noqa: E402
from randomizer.test_start import (ANALYZED_INFO, HOOK_FLOW, StartPreset, apply_start,  # noqa: E402
                                   chain_calls, subflow_closure, with_subflow_list)

PRESET = StartPreset('HyruleField_Child', 'HyruleField_FrontOfLostWoodBridge',
                     items=('Item_Ocarina_Fairy',))


def _grow(rstb: Rstb, rel: str, old_len: int, new_len: int) -> None:
    orig = rstb.get(rel)
    if orig is None:
        raise SystemExit(f'FAIL: the RSTB does not have {rel}')
    rstb.set(rel, orig + ((max(new_len - old_len, 0) + 0xFF) & ~0xFF) + 0x1000)


def build(nup: NupArchive, preset: StartPreset) -> dict[str, bytes]:
    """{romfs path: compressed bytes} of the hook flow, the event info table and the RSTB."""
    codec = ZsCodec.from_archive(nup)

    def load(name: str) -> EventFlow | None:
        p = f'Event/EventFlow/{name}.bfevfl.zs'
        return EventFlow(codec.decompress(p, nup.read(p))) if nup.has(p) else None

    rel = f'Event/EventFlow/{HOOK_FLOW}.bfevfl'
    raw = codec.decompress(rel + '.zs', nup.read(rel + '.zs'))
    new = apply_start(raw, preset)
    info = codec.decompress(ANALYZED_INFO, nup.read(ANALYZED_INFO))
    new_info = with_subflow_list(info, HOOK_FLOW, subflow_closure(load, chain_calls(preset)))
    rstb = Rstb.load(codec.decompress(RSTB_PATH, nup.read(RSTB_PATH)))
    _grow(rstb, rel, len(raw), len(new))
    _grow(rstb, ANALYZED_INFO[:-3], len(info), len(new_info))
    return {rel + '.zs': codec.compress(rel + '.zs', new),
            ANALYZED_INFO: codec.compress(ANALYZED_INFO, new_info),
            RSTB_PATH: codec.compress(RSTB_PATH, rstb.dump())}


def main() -> None:
    nup_path, out = sys.argv[1:3]
    out_p = Path(out)
    tmp = out_p.with_name(out_p.name + '.tmp')
    shutil.rmtree(tmp, ignore_errors=True)
    with NupArchive(nup_path) as nup:
        files = build(nup, PRESET)
    for rel, data in files.items():
        p = tmp / 'romfs' / Path(*rel.split('/'))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    shutil.rmtree(out_p, ignore_errors=True)
    tmp.rename(out_p)
    print('\n'.join(files))


if __name__ == '__main__':
    main()
