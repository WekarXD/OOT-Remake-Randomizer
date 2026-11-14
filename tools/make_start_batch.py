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
from randomizer.test_start import (ANALYZED_INFO, HOOK_FLOW, START_POS, StartPreset,  # noqa: E402
                                   apply_start, chain_calls, subflow_closure, with_start_pos,
                                   with_subflow_list)

PRESET = StartPreset('HyruleField_Child', 'HyruleField_FrontOfLostWoodBridge',
                     items=('Item_Ocarina_Fairy',))


FLOW_DIR, FLOW_EXT = 'Event/EventFlow/', '.bfevfl.zs'


class Batch:
    """The decompressed files a test batch changes, built on the game's files or on
    a given base (e.g. the full skip's flows)."""

    def __init__(self, nup: NupArchive, base: dict[str, bytes] | None = None) -> None:
        self.nup = nup
        self.codec = ZsCodec.from_archive(nup)
        self.files: dict[str, bytes] = dict(base or {})  # romfs path -> decompressed

    def original(self, path: str) -> bytes:
        raw = self.nup.read(path)
        return self.codec.decompress(path, raw) if path.endswith('.zs') else raw

    def unpack(self, files: dict[str, bytes]) -> dict[str, bytes]:
        """`files` (romfs path -> bytes as written to the mod) decompressed."""
        return {p: self.codec.decompress(p, d) if p.endswith('.zs') else d
                for p, d in files.items()}

    def read(self, path: str) -> bytes:
        """The batch's current version of `path` (the game's if unchanged)."""
        return self.files[path] if path in self.files else self.original(path)

    def flow(self, name: str) -> EventFlow | None:
        path = FLOW_DIR + name + FLOW_EXT
        return EventFlow(self.read(path)) if path in self.files or self.nup.has(path) else None

    def compressed(self) -> dict[str, bytes]:
        """{romfs path: compressed bytes} of every changed file plus the RSTB, whose
        entry for each file that grew (against the game's) is raised to fit it."""
        rstb = Rstb.load(self.original(RSTB_PATH))
        out = {}
        for path, data in sorted(self.files.items()):
            key = path[:-3] if path.endswith('.zs') else path
            grow = len(data) - len(self.original(path))
            if grow > 0:
                size = rstb.get(key)
                if size is None:
                    print(f'WARNING: no RSTB entry for grown {path}', file=sys.stderr)
                else:
                    rstb.set(key, size + ((grow + 0xFF) & ~0xFF) + 0x1000)
            out[path] = self.codec.compress(path, data) if path.endswith('.zs') else data
        out[RSTB_PATH] = self.codec.compress(RSTB_PATH, rstb.dump())
        return out


def add_start(batch: Batch, preset: StartPreset) -> None:
    """Applies `preset` to the batch: the hook flow, the event info table and, if
    the preset adds a start position, the start position table."""
    if preset.new_pos is not None and preset.new_pos.name != preset.start_pos:
        raise SystemExit('FAIL: start_pos must name the new start position')
    hook = FLOW_DIR + HOOK_FLOW + FLOW_EXT
    batch.files[hook] = apply_start(batch.read(hook), preset)
    batch.files[ANALYZED_INFO] = with_subflow_list(
        batch.read(ANALYZED_INFO), HOOK_FLOW, subflow_closure(batch.flow, chain_calls(preset)))
    if preset.new_pos is not None:
        batch.files[START_POS] = with_start_pos(batch.read(START_POS), preset.banc,
                                                preset.new_pos)


def build(nup: NupArchive, preset: StartPreset) -> dict[str, bytes]:
    """{romfs path: compressed bytes} of the preset's files plus the RSTB."""
    batch = Batch(nup)
    add_start(batch, preset)
    return batch.compressed()


def write_mod(out: str, files: dict[str, bytes]) -> None:
    """Writes `files` under <out>/romfs (built in <out>.tmp, then swapped in)."""
    out_p = Path(out)
    tmp = out_p.with_name(out_p.name + '.tmp')
    shutil.rmtree(tmp, ignore_errors=True)
    for rel, data in files.items():
        p = tmp / 'romfs' / Path(*rel.split('/'))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    shutil.rmtree(out_p, ignore_errors=True)
    tmp.rename(out_p)
    print('\n'.join(files))


def main() -> None:
    nup_path, out = sys.argv[1:3]
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, PRESET))


if __name__ == '__main__':
    main()
