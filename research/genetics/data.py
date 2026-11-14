"""Strict Ped-sim .tot parser and conservative family-group splitting."""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re

PAIRS_PER_BATCH = 50000


@dataclass
class Summary:
    cousin: int
    observed: dict[int, tuple[float, int]]
    ibd2_positive_pairs: int
    positive_rows: int
    zero_pairs: int
    omitted_zero_pairs: int
    excluded: dict[int, str]

    def records(self):
        # These zeros are documented omissions, not generated biological observations.
        for replicate in range(1, PAIRS_PER_BATCH + 1):
            if replicate in self.excluded:
                continue
            cm, segments = self.observed.get(replicate, (0.0, 0))
            yield replicate, cm, segments


def parse_tot(text, cousin, pairs_per_batch=PAIRS_PER_BATCH):
    if not 1 <= cousin <= 8 or pairs_per_batch != PAIRS_PER_BATCH:
        raise ValueError("Only the documented eight-class,50000-pair scope is supported")
    lines = text.splitlines()
    if not lines or lines[0].split() != ["id", "IBD1", "IBD2", "total", "n_seg"]:
        raise ValueError("Unexpected .tot schema/header")
    observed, ibd2_count, seen, excluded = {}, 0, set(), {}
    pattern = re.compile(rf"{cousin}c([1-9]\d*)_g{cousin + 2}-b1-i1")
    for number, line in enumerate(lines[1:], 2):
        fields = line.split()
        if len(fields) != 5:
            # The source awk emits an empty IBD1/n_seg field for an IBD2-only pair.
            fields = line.split(" ")
            if len(fields) != 5:
                raise ValueError(f"Malformed .tot row at line{number}")
            fields = [v or "0" for v in fields]
        match = pattern.fullmatch(fields[0])
        if not match:
            raise ValueError(f"Unexpected replicate ID at line{number}")
        replicate = int(match[1])
        if not 1 <= replicate <= pairs_per_batch or replicate in seen:
            raise ValueError("Duplicate/out-of-universe replicate ID")
        seen.add(replicate)
        ibd1, ibd2, total = map(float, fields[1:4])
        segments_float = float(fields[4])
        if not all(math.isfinite(v) and v >= 0 for v in (ibd1, ibd2, total, segments_float)):
            raise ValueError("Nonfinite/negative source summary")
        if not segments_float.is_integer() or (ibd1 > 0 and segments_float < 1):
            raise ValueError("Invalid IBD1 segment count")
        if not math.isclose(total, ibd1 + 2 * ibd2, rel_tol=2e-5, abs_tol=0.0001):
            raise ValueError("Weighted total disagrees with IBD1/IBD2 columns")
        if total == 0 and segments_float > 0:
            excluded[replicate] = "Source reports zero total but positive segment count; unresolved rounding/zero-length anomaly. Retained in QC, not modeled or imputed."
            continue
        observed[replicate] = (total, int(segments_float))
        ibd2_count += ibd2 > 0
    omitted = pairs_per_batch - len(seen)
    return Summary(cousin, observed, ibd2_count, sum(cm > 0 for cm, _ in observed.values()), omitted + sum(cm == 0 for cm, _ in observed.values()), omitted, excluded)


def load_summary(path: Path, cousin, expected_sha256):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Source hash mismatch: {path.name}")
    return parse_tot(raw.decode("utf8"), cousin)


def group_partition(cousin, replicate):
    # Same relationship/replicate is held together across model and batch names.
    digest = hashlib.sha256(f"kinfold-genetics-v1|{cousin}:{replicate}".encode()).digest()
    value = int.from_bytes(digest[:8], "big") % 10000
    return "train" if value < 6000 else "calibration" if value < 8000 else "test"


def partitions():
    return {cousin: [None] + [group_partition(cousin, i) for i in range(1, PAIRS_PER_BATCH + 1)] for cousin in range(1, 9)}
