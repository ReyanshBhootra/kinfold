"""Explicitly fabricated fallible-record layer. No real historical data or AI."""
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import math
import random


@dataclass(frozen=True)
class Record:
    document_id: str
    origin: str | None
    claimed_cousin: int
    assumed_reliability: float


def fabricated_records(truth, replicate, scenario="nominal_single_copy"):
    rng = random.Random(int.from_bytes(hashlib.sha256(f"kinfold-record-stress-v1|{truth}:{replicate}".encode()).digest()[:8], "big"))
    output = []
    for origin, assumed in [("A", 0.85), ("B", 0.7)]:
        missing_draw, correct_draw, wrong = rng.random(), rng.random(), rng.randrange(7)
        missing = 0.7 if scenario == "missing_70_percent" else 0.25
        actual = 0.55 if origin == "A" and scenario == "A_wrong_rate_45_percent_copied_six_times" else assumed
        label = truth if correct_draw < actual else [c for c in range(1, 9) if c != truth][wrong]
        if missing_draw < missing:
            continue
        copies = 6 if origin == "A" and scenario.startswith("A_") else 1
        lineage = None if scenario.endswith("lineage_unknown") else origin
        output += [Record(f"doc-{origin}-{copy}", lineage, label, assumed) for copy in range(copies)]
    return output


def fused_scores(dna_scores, records, grouped=True):
    if len(dna_scores) != 8 or not all(math.isfinite(p) and p > 0 for p in dna_scores):
        raise ValueError("Eight finite positive reference scores required")
    evidence = list(records)
    if grouped:
        origins = defaultdict(list)
        for record in records:
            if record.origin is not None:
                origins[record.origin].append(record)
        # Unknown lineage cannot establish independence. Conflicting copies are not
        # resolved by majority vote; the entire conflicted origin contributes no weight.
        evidence = [values[0] for values in origins.values() if len({(r.claimed_cousin, r.assumed_reliability) for r in values}) == 1]
    scores = [math.log(p) for p in dna_scores]
    for record in evidence:
        if not 1 <= record.claimed_cousin <= 8 or not 1 / 8 < record.assumed_reliability < 1:
            raise ValueError("Invalid fabricated record assertion/reliability")
        for i in range(8):
            probability = record.assumed_reliability if i + 1 == record.claimed_cousin else (1 - record.assumed_reliability) / 7
            scores[i] += math.log(probability)
    maximum = max(scores); values = [math.exp(value - maximum) for value in scores]; total = sum(values)
    return tuple(v / total for v in values)


def choose_verification(scores, records, grouped=True):
    options = {}
    for record in records:
        key = record.origin if grouped and record.origin else record.document_id
        options.setdefault(key, record)
    if not options:
        return None
    def gain(record):
        p = scores[record.claimed_cousin - 1]
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p) if 0 < p < 1 else 0
    return max(sorted(options.values(), key=lambda r: r.document_id), key=gain)


def oracle_log_gain(scores, record, truth):
    """Evaluation-only perfect correctness answer; not a real source verification model."""
    if record is None:
        return 0.0
    p = scores[record.claimed_cousin - 1]
    return -math.log(max(scores[truth - 1], 1e-300)) if record.claimed_cousin == truth else -math.log(max(1 - p, 1e-300))
