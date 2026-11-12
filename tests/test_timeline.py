import os
import struct
import unittest

from randomizer.formats.timeline import Timeline, TimelineError, retime
from randomizer.timeline_skip import (LASTING, MOVIE_SPIKE_TIMELINES, SPIKE_TIMELINES,
                                      build_timeline_spike_files, new_length, shorten)

NUP_PATH = os.environ.get('OOT_NUP')


def _str(s: str) -> bytes:
    b = struct.pack('<H', len(s)) + s.encode() + b'\0'
    return b + b'\0' * (len(b) % 2)


def make_timeline(duration, clips, subs=()):
    """Minimal timeline-only BFEVFL. clips: (start, dur, actor, action)."""
    actors = sorted({c[2] for c in clips})
    acts = {a: sorted({c[3] for c in clips if c[2] == a}) for a in actors}
    buf = bytearray(0x48)
    buf[:6] = b'BFEVFL'
    struct.pack_into('<HH', buf, 0x20, 0, 1)

    def put(b: bytes) -> int:
        while len(buf) % 8:
            buf.append(0)
        off = len(buf)
        buf.extend(b)
        return off

    tl_list = put(b'\0' * 8)
    struct.pack_into('<Q', buf, 0x38, tl_list)
    tl = put(b'\0' * 0x68)
    struct.pack_into('<Q', buf, tl_list, tl)
    buf[tl:tl + 4] = b'TLIN'
    struct.pack_into('<f6H', buf, tl + 0x10, duration, len(actors), 0, len(clips), 0, len(subs), 0)
    struct.pack_into('<Q', buf, tl + 0x20, put(_str('T')))
    actor_block = put(b'\0' * 0x38 * len(actors))
    struct.pack_into('<Q', buf, tl + 0x28, actor_block)
    for i, a in enumerate(actors):
        names = [put(_str(x)) for x in acts[a]]
        table = put(b''.join(struct.pack('<Q', n) for n in names))
        struct.pack_into('<Q', buf, actor_block + 0x38 * i, put(_str(a)))
        struct.pack_into('<Q', buf, actor_block + 0x38 * i + 0x18, table)
        struct.pack_into('<H', buf, actor_block + 0x38 * i + 0x30, len(names))
    clip_block = put(b'\0' * 0x18 * len(clips))
    struct.pack_into('<Q', buf, tl + 0x30, clip_block)
    for i, (start, dur, a, act) in enumerate(clips):
        struct.pack_into('<ffHH', buf, clip_block + 0x18 * i, start, dur,
                         actors.index(a), acts[a].index(act))
    names = [put(_str(s)) for s in subs]
    struct.pack_into('<Q', buf, tl + 0x48, put(b''.join(struct.pack('<Q', n) for n in names)))
    return bytes(buf)


FADE = 'EventEventFadeInForTimeline'
WARP = 'EventWarpToTargetPosAndRot'


class TimelineFormatTest(unittest.TestCase):
    def test_reads_clips_and_subtimelines(self):
        tl = Timeline(make_timeline(300.0, [(0, 30, 'UI', FADE), (100, 50, 'Cam', 'Move')], ['T_Env']))
        self.assertEqual(tl.duration, 300.0)
        self.assertEqual([(c.start, c.actor, c.action) for c in tl.clips],
                         [(0.0, 'UI', FADE), (100.0, 'Cam', 'Move')])
        self.assertEqual(tl.subtimelines, ['T_Env'])

    def test_rejects_flowchart_files(self):
        data = bytearray(make_timeline(10.0, []))
        struct.pack_into('<H', data, 0x20, 1)
        with self.assertRaises(TimelineError):
            Timeline(bytes(data))

    def test_retime_keeps_size_and_rejects_unknown_clip(self):
        data = make_timeline(300.0, [(100, 50, 'Cam', 'Move')])
        out = retime(data, 5.0, {Timeline(data).clips[0].offset: (4.0, 1.0)})
        self.assertEqual(len(out), len(data))
        tl = Timeline(out)
        self.assertEqual((tl.duration, tl.clips[0].start, tl.clips[0].duration), (5.0, 4.0, 1.0))
        with self.assertRaises(TimelineError):
            retime(data, 5.0, {3: (0.0, 1.0)})


class ShortenTest(unittest.TestCase):
    def test_cut_after_opening_fade_in(self):
        tl = Timeline(shorten(make_timeline(900.0, [(25, 35, 'UI', FADE), (300, 40, 'Voice', 'Talk')])))
        self.assertEqual(tl.duration, 60.0)

    def test_late_fade_in_is_ignored(self):
        self.assertEqual(new_length(Timeline(make_timeline(900.0, [(500, 30, 'UI', FADE)]))), 1.0)

    def test_lasting_clips_move_before_the_end(self):
        tl = Timeline(shorten(make_timeline(900.0, [(0, 15, 'UI', FADE), (800, 1, 'Player', WARP),
                                                    (300, 40, 'Voice', 'Talk')])))
        warp = next(c for c in tl.clips if c.action == WARP)
        talk = next(c for c in tl.clips if c.action == 'Talk')
        self.assertEqual((tl.duration, warp.start, warp.duration), (15.0, 14.0, 1.0))
        self.assertEqual(talk.start, 300.0)  # past the end: never plays
        self.assertIn(WARP, LASTING)

    def test_never_longer_than_original(self):
        self.assertEqual(Timeline(shorten(make_timeline(10.0, [(0, 60, 'UI', FADE)]))).duration, 10.0)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class RealTimelineTest(unittest.TestCase):
    def test_spike_files(self):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        with NupArchive(NUP_PATH) as nup:
            names = SPIKE_TIMELINES + MOVIE_SPIKE_TIMELINES
            files = build_timeline_spike_files(nup, names)
            codec = ZsCodec.from_archive(nup)
            for name in names:
                path = f'Event/EventFlow/{name}.bfevfl.zs'
                old = Timeline(codec.decompress(path, nup.read(path)))
                new = Timeline(codec.decompress(path, files[path]))
                self.assertEqual(new.duration, new_length(old), name)
                for sub in old.subtimelines:  # some are missing (Dm_Kokiri_0000_Effect)
                    sub_path = f'Event/EventFlow/{sub}.bfevfl.zs'
                    self.assertEqual(sub_path in files, nup.has(sub_path), sub)
                for o, n in zip(old.clips, new.clips):
                    if o.action in LASTING:
                        self.assertLess(n.start, new.duration, (name, o.action))
