# tests

import unittest
import re
from main import CountMinSketch, StreamSummary, process_stream

class TestCountMinSketch(unittest.TestCase):
    def test_initial_estimate_zero(self):
        cms = CountMinSketch(depth=3, width=100)
        self.assertEqual(cms.estimate("foo"), 0)
        self.assertEqual(cms.estimate("bar"), 0)

    def test_update_and_estimate(self):
        cms = CountMinSketch(depth=4, width=50)
        cms.update("alpha", 5)
        self.assertEqual(cms.estimate("alpha"), 5)
        cms.update("alpha", 3)
        self.assertEqual(cms.estimate("alpha"), 8)

    def test_decrement_below_zero(self):
        cms = CountMinSketch(depth=2, width=20)
        cms.update("x", 4)
        self.assertEqual(cms.estimate("x"), 4)
        cms.update("x", -1)
        self.assertEqual(cms.estimate("x"), 3)
        cms.update("x", -5)
        self.assertEqual(cms.estimate("x"), -2)

    def test_hash_positions_vary(self):
        cms = CountMinSketch(depth=2, width=10)
        posns = {cms._idx(f"key{i}", salt)
                  for i in range(20) for salt in range(cms.depth)}
        self.assertTrue(len(posns) > 10)

class TestStreamSummary(unittest.TestCase):
    def test_add_within_capacity(self):
        ss = StreamSummary(capacity=2)
        ss.add("a", 1)
        ss.add("b", 1)
        top = ss.topk()
        self.assertEqual(len(top), 2)
        self.assertIn(("a", 1), top)
        self.assertIn(("b", 1), top)

    def test_add_eviction(self):
        ss = StreamSummary(capacity=2)
        ss.add("a", 1)
        ss.add("b", 1)
        ss.add("c", 1)
        top = dict(ss.topk())
        self.assertIn("c", top)

    def test_topk_tiebreak_lex(self):
        ss = StreamSummary(capacity=3)
        ss.add("b", 2)
        ss.add("a", 2)
        ss.add("c", 2)
        top = ss.topk()
        self.assertEqual([f for f,_ in top], ["a","b","c"] )

class TestProcessStream(unittest.TestCase):
    def setUp(self):
        self.depth = 3
        self.width = 50

    def test_empty_events(self):
        out = process_stream([], W=10, k=3,
                             sketch_depth=self.depth,
                             sketch_width=self.width)
        self.assertEqual(out, [])

    def test_single_event_format_and_count(self):
        logs = [(100, "fieldA")]
        out = process_stream(logs, W=5, k=1,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        self.assertEqual(len(out), 1)
        # strict format with spaces after commas
        self.assertRegex(out[0], r"^100 \[[^,]+:[0-9]+(?:, [^,]+:[0-9]+)*\]$")
        inner = re.match(r"^\d+ \[(.+)\]$", out[0]).group(1)
        self.assertEqual(inner, "fieldA:1")

    def test_padding_when_less_than_k(self):
        logs = [(1, "x"), (2, "y")]
        out = process_stream(logs, W=10, k=4,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        for idx, (t, _) in enumerate(logs):
            parts = re.match(r"^\d+ \[(.*)\]$", out[idx]).group(1).split(', ')
            self.assertEqual(len(parts), 4)
            seen_names = {p.split(":")[0] for p in parts}
            self.assertTrue("x" in seen_names)
            self.assertTrue("y" in seen_names)
            # one slot should be the lex smallest unseen field (e.g. 'a','b',...)
            unseen = [p for p in parts if p.split(':')[1]=='0']
            self.assertTrue(len(unseen) >= 1)

    def test_empty_string_padding(self):
        logs = [(1, "a")]
        out = process_stream(logs, W=1, k=3,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        parts = out[0].split('[')[1].rstrip(']').split(', ')
        names = [p.split(':')[0] for p in parts]
        # only 'a' seen, so we expect two empty-string slots to reach k=3
        self.assertEqual(names.count(''), 2)

    def test_sliding_window_eviction(self):
        logs = [(1, "x"), (2, "y"), (15, "x")]
        # W=10 → window is [t-9, t], so event at t=2 should be evicted at t=15
        out = process_stream(logs, W=10, k=2,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        inner = out[-1].split('[')[1].rstrip(']')
        parts = inner.split(', ')
        counts = {name: int(cnt) for name,cnt in (p.split(':') for p in parts)}
        self.assertEqual(counts["x"], 1)
        self.assertEqual(counts["y"], 0)

    def test_identical_timestamps(self):
        logs = [(5,"a"), (5,"b"), (5,"c")]
        out = process_stream(logs, W=1, k=2,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        inner = re.match(r"^\d+ \[(.*)\]$", out[0]).group(1).split(', ')
        self.assertEqual(inner[0].split(':')[0], "a")
        self.assertEqual(inner[1].split(':')[0], "b")

    def test_zero_window_size(self):
        logs = [(10,"f1"), (20,"f1")]
        out = process_stream(logs, W=0, k=1,
                              sketch_depth=self.depth,
                              sketch_width=self.width)
        self.assertEqual(out[0], "10 [f1:1]")
        self.assertEqual(out[1], "20 [f1:1]")

if __name__ == "__main__":
    unittest.main()
