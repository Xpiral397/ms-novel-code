import sys
import collections
import hashlib
from typing import List, Tuple, Dict, Deque

class CountMinSketch:
    def __init__(self, depth: int, width: int):
        self.depth = depth
        self.width = width
        self.table = [[0] * width for _ in range(depth)]
        self.salts = list(range(depth))

    def _idx(self, key: str, salt: int) -> Tuple[int, int]:
        data = f"{salt}-{key}".encode("utf-8")
        digest = hashlib.sha256(data).digest()
        val = int.from_bytes(digest, "big")
        return salt, val % self.width

    def update(self, key: str, delta: int = 1) -> None:
        for salt in self.salts:
            row, col = self._idx(key, salt)
            self.table[row][col] += delta

    def estimate(self, key: str) -> int:
        min_val = float("inf")
        for salt in self.salts:
            row, col = self._idx(key, salt)
            cnt = self.table[row][col]
            if cnt < min_val:
                min_val = cnt
        return int(min_val) if min_val != float("inf") else 0

class StreamSummary:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.counters: Dict[str, int] = {}

    def add(self, key: str, count: int) -> None:
        if key in self.counters:
            self.counters[key] += count
        elif len(self.counters) < self.capacity:
            self.counters[key] = count
        else:
            to_remove = []
            for k in list(self.counters):
                self.counters[k] -= count
                if self.counters[k] <= 0:
                    to_remove.append(k)
            for k in to_remove:
                del self.counters[k]
            if len(self.counters) < self.capacity:
                self.counters[key] = count

    def decrement(self, key: str, count: int) -> None:
        if key in self.counters:
            self.counters[key] -= count
            if self.counters[key] <= 0:
                del self.counters[key]

    def topk(self) -> List[Tuple[str, int]]:
        items = list(self.counters.items())
        items.sort(key=lambda x: (-x[1], x[0]))
        return items[:self.capacity]


def process_stream(
    events: List[Tuple[int, str]],
    W: int,
    k: int,
    sketch_depth: int,
    sketch_width: int
) -> List[str]:
    # Precompute all distinct fields for padding (global list)
    distinct_fields = sorted({f for _, f in events})

    cms = CountMinSketch(sketch_depth, sketch_width)
    summary = StreamSummary(k)
    buffer: Deque[Tuple[int, str]] = collections.deque()
    results: List[str] = []

    for t, field in events:
        # ingest
        cms.update(field, 1)
        summary.add(field, 1)
        buffer.append((t, field))

        # evict old events
        if W == 0:
            while buffer and buffer[0][0] < t:
                old_t, old_f = buffer.popleft()
                cms.update(old_f, -1)
                summary.decrement(old_f, 1)
        else:
            cutoff = t - W
            while buffer and buffer[0][0] <= cutoff:
                old_t, old_f = buffer.popleft()
                cms.update(old_f, -1)
                summary.decrement(old_f, 1)

        # get top-k candidates and re-rank by CMS estimates
        candidates = [f for f, _ in summary.topk()]
        est_list = [(f, cms.estimate(f)) for f in candidates]
        est_list.sort(key=lambda x: (-x[1], x[0]))
        top = est_list[:k]

        # pad with lexicographically smallest distinct fields not in top
        present = {f for f, _ in top}
        for f in distinct_fields:
            if len(top) >= k:
                break
            if f not in present:
                top.append((f, 0))
                present.add(f)

        # pad with empty strings if still under k
        while len(top) < k:
            top.append(("", 0))

        # format output with comma+space
        line = f"{t} [" + ", ".join(f"{f}:{c}" for f, c in top) + "]"
        results.append(line)

    return results

if __name__ == "__main__":
    data = sys.stdin
    header = next(data).split()
    N, W, k = map(int, header)
    events: List[Tuple[int, str]] = []
    for _ in range(N):
        parts = next(data).strip().split()
        if not parts:
            continue
        t = int(parts[0]); field = parts[1]
        events.append((t, field))

    sketch_depth = 5
    sketch_width = max(1000, k * 10)
    for line in process_stream(events, W, k, sketch_depth, sketch_width):
        print(line)


