import random
import unittest

from randomizer.evtrim import compute_trim
from randomizer.formats.bfevfl import ACTION, FORK, JOIN, SWITCH, Event

END = 0xFFFF


def act(i, nxt):
    return Event(index=i, kind=ACTION, next=nxt)


class TrimTests(unittest.TestCase):
    def test_linear_chain(self):
        ev = [act(0, 1), act(1, 2), act(2, END)]
        self.assertEqual(compute_trim(ev, {1}), ({1}, {1: 2}))

    def test_tail_to_end(self):
        ev = [act(0, 1), act(1, 2), act(2, END)]
        removed, rt = compute_trim(ev, {1, 2})
        self.assertEqual(removed, {1, 2})
        self.assertEqual(rt[1], END)
        self.assertEqual(rt[2], END)

    def test_cycle_of_removed(self):
        ev = [act(0, 1), act(1, 2), act(2, 1)]
        removed, rt = compute_trim(ev, {1, 2})
        self.assertEqual(rt, {1: END, 2: END})

    def test_non_action_never_removed(self):
        ev = [act(0, 1), Event(index=1, kind=SWITCH, cases=[2]),
              Event(index=2, kind=FORK, forks=[3], join=4), act(3, 4),
              Event(index=4, kind=JOIN, next=END)]
        removed, rt = compute_trim(ev, {1, 2, 4})
        self.assertEqual(removed, set())
        self.assertEqual(rt, {})

    def test_fork_branch_kept(self):
        ev = [Event(index=0, kind=FORK, forks=[1, 3], join=5),
              act(1, 2), act(2, 5), act(3, 4), act(4, 5),
              Event(index=5, kind=JOIN, next=END)]
        removed, rt = compute_trim(ev, {1, 2, 3})
        self.assertNotIn(1, removed)
        self.assertIn(2, removed)
        self.assertEqual(rt[3], 4)
        self.assertEqual(rt[2], 5)

    def test_fork_branch_to_end_kept(self):
        ev = [Event(index=0, kind=FORK, forks=[1], join=2), act(1, END),
              Event(index=2, kind=JOIN, next=END)]
        removed, _ = compute_trim(ev, {1})
        self.assertEqual(removed, set())

    def test_contraction_property(self):
        rng = random.Random(1234)
        n = 50
        ev = []
        for i in range(n):
            if rng.random() < 0.25:
                ev.append(Event(index=i, kind=SWITCH,
                                cases=[rng.choice([*range(n), END]) for _ in range(3)]))
            else:
                ev.append(act(i, rng.choice([*range(n), END])))
        removable = {i for i in range(n) if rng.random() < 0.5}
        removed, rt = compute_trim(ev, removable)
        self.assertTrue(removed <= removable)
        for r in removed:
            self.assertTrue(rt[r] == END or rt[r] not in removed)

        def walk(start, choices, trimmed):
            seq, cur, steps = [], start, 0
            while cur != END and steps < 500:
                steps += 1
                if trimmed and cur in removed:
                    cur = rt[cur]
                    continue
                e = ev[cur]
                if e.kind == ACTION:
                    seq.append(cur)
                    cur = e.next
                else:
                    cur = e.cases[choices[cur % len(choices)] % len(e.cases)]
            return seq

        for start in range(n):
            for ch in ([0], [1], [2], [0, 2, 1]):
                orig = [i for i in walk(start, ch, False) if i not in removed]
                got = walk(start, ch, True)
                # original walk is capped by steps; compare common prefix length
                m = min(len(orig), len(got))
                self.assertEqual(orig[:m], got[:m])


if __name__ == '__main__':
    unittest.main()
