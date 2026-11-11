"""BFEVFL timeline (`TLIN`) reader and duration patcher.

261 of the game's `Dm_*` flow files hold one timeline and no flowchart
(header 0x20 u16 = 0 flowcharts, 0x22 u16 = 1 timeline; 0x38 u64 -> list of
timeline pointers).

Timeline (offsets from its start):
  0x00 `TLIN`; 0x10 f32 duration in frames; 0x14 u16 counts of actors,
  actions, clips, one-shots, subtimelines and cuts;
  0x20 u64 name; 0x28 actors; 0x30 clips; 0x38 one-shots; 0x40 triggers;
  0x48 subtimelines; 0x50 cuts; 0x60 parameters.
Actor (0x38 bytes, as in flowcharts): +0x00 name, +0x18 actions (u64 -> u64
  string pointers), +0x30 u16 number of actions.
Clip (0x18 bytes): f32 start, f32 duration, u16 actor, u16 action (index in
  that actor's actions), u32, u64 parameters.
Subtimeline: u64 -> name (a timeline in another file, e.g. `<scene>_Effect`).
Cut (0x18 bytes): f32 start, u32, u64 name, u64 parameters.
"""
import struct
from dataclasses import dataclass


class TimelineError(Exception):
    pass


@dataclass
class Clip:
    start: float
    duration: float
    actor: str
    action: str
    offset: int  # of the clip's start in the file


class Timeline:
    def __init__(self, data: bytes):
        self._d = data
        try:
            self._parse()
        except (struct.error, IndexError, UnicodeDecodeError) as e:
            raise TimelineError(f'Invalid timeline: {e}') from e

    def _u16(self, o):
        return struct.unpack_from('<H', self._d, o)[0]

    def _u64(self, o):
        return struct.unpack_from('<Q', self._d, o)[0]

    def _str(self, p):
        return self._d[p + 2:p + 2 + self._u16(p)].decode('utf-8') if p else None

    def _parse(self):
        d = self._d
        if d[:6] != b'BFEVFL':
            raise TimelineError('BFEVFL header missing.')
        if self._u16(0x20) != 0 or self._u16(0x22) != 1:
            raise TimelineError('Not a timeline-only file.')
        t = self._u64(self._u64(0x38))
        if d[t:t + 4] != b'TLIN':
            raise TimelineError('TLIN header missing.')
        self.offset = t
        self.duration = struct.unpack_from('<f', d, t + 0x10)[0]
        n_actors, _, n_clips, _, n_sub, n_cuts = struct.unpack_from('<6H', d, t + 0x14)
        self.name = self._str(self._u64(t + 0x20))
        actors = []
        for i in range(n_actors):
            a = self._u64(t + 0x28) + 0x38 * i
            acts = self._u64(a + 0x18)
            actors.append((self._str(self._u64(a)),
                           [self._str(self._u64(acts + 8 * j)) for j in range(self._u16(a + 0x30))]))
        self.clips = []
        for i in range(n_clips):
            c = self._u64(t + 0x30) + 0x18 * i
            start, dur = struct.unpack_from('<ff', d, c)
            ai, ki = self._u16(c + 8), self._u16(c + 10)
            name, acts = actors[ai]
            self.clips.append(Clip(start, dur, name, acts[ki], c))
        self.subtimelines = [self._str(self._u64(self._u64(t + 0x48) + 8 * i)) for i in range(n_sub)]
        self.cuts = [struct.unpack_from('<f', d, self._u64(t + 0x50) + 0x18 * i)[0] for i in range(n_cuts)]


def retime(data: bytes, frames: float, clips: dict[int, tuple[float, float]] = {}) -> bytes:
    """The same file with the timeline's duration set to `frames` and the clips
    at the given offsets moved to (start, duration)."""
    tl = Timeline(data)
    if not set(clips) <= {c.offset for c in tl.clips}:
        raise TimelineError('Unknown clip offset.')
    out = bytearray(data)
    struct.pack_into('<f', out, tl.offset + 0x10, frames)
    for off, (start, dur) in clips.items():
        struct.pack_into('<ff', out, off, start, dur)
    return bytes(out)
