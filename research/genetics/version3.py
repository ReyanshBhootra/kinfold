"""Version 3: a label-free, source-level reliability check before record fusion.

v2 fused any complete, known A/B bundle at its *assumed* reliability. When a
source was really worse than assumed, coverage fell (0.757 at nominal 0.90).
A reliability cannot be judged from one record, so v3 checks each source across
a batch of cases that cite it, without ground-truth labels:

    residual_i = DNA score of the claimed degree - its expectation if the
                 source had its assumed reliability (using DNA scores as weights)

The batch mean residual is compared with a reference distribution measured on
v2-calibration rows whose fabricated records really have the assumed
reliability. A one-sided z-test (alpha 0.005 per origin) rejects sources that
agree with the DNA evidence significantly worse than assumed. Rejected or
under-evidenced sources disable fusion for that batch; affected rows use DNA
scores with DNA calibration (the v2 fallback).

Honesty notes recorded in the protocol: v3 was designed after seeing the v2
incorrect-reliability failure on the same evaluation rows; four new scenarios
were added before any v3 result was computed; data are a reanalysis, not fresh.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import NormalDist
import time

from .baseline import HistogramModel
from .data import group_partition, load_summary
from .records import Record, fused_scores
from .version2 import (
    RELIABILITY, Calibration, Metrics, Scores, checked_set, complete_bundle,
    corrected_prediction, digest, partition_v2, safe_json,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/v3"
V2_OUT = ROOT / "results/v2"
RECORD_SALT = "kinfold-fallback-v2-records-20261114"  # same draws as v2: common random numbers
BATCH_SALT = "kinfold-reliability-v3-batches-20261114"
ALPHA_PER_ORIGIN = 0.005
Z_CRITICAL = NormalDist().inv_cdf(1 - ALPHA_PER_ORIGIN)
MIN_RECORDS = 10
BATCH_SIZES = (25, 100, 400, "all")
NOMINAL = {"A": 0.85, "B": 0.7}

SCENARIOS = {
    # The six v2 scenarios (results already seen before v3 was designed).
    "clean_complete": {"actual": NOMINAL, "missing": 0.0, "unknown": [], "seen_before_design": True},
    "nominal_missing25": {"actual": NOMINAL, "missing": 0.25, "unknown": [], "seen_before_design": True},
    "missing70": {"actual": NOMINAL, "missing": 0.7, "unknown": [], "seen_before_design": True},
    "incorrect_A45_complete": {"actual": {"A": 0.55, "B": 0.7}, "missing": 0.0, "unknown": [], "seen_before_design": True},
    "unknown_all_complete": {"actual": NOMINAL, "missing": 0.0, "unknown": ["A", "B"], "seen_before_design": True},
    "unknown_A_complete": {"actual": NOMINAL, "missing": 0.0, "unknown": ["A"], "seen_before_design": True},
    # New scenarios fixed in the protocol before any v3 evaluation.
    "incorrect_A25_complete": {"actual": {"A": 0.75, "B": 0.7}, "missing": 0.0, "unknown": [], "seen_before_design": False},
    "incorrect_B_complete": {"actual": {"A": 0.85, "B": 0.45}, "missing": 0.0, "unknown": [], "seen_before_design": False},
    "incorrect_A45_missing25": {"actual": {"A": 0.55, "B": 0.7}, "missing": 0.25, "unknown": [], "seen_before_design": False},
    "better_A_complete": {"actual": {"A": 0.95, "B": 0.7}, "missing": 0.0, "unknown": [], "seen_before_design": False},
}


def scenario_records(truth, replicate, scenario):
    """Mirror v2's draw order exactly, with per-origin actual reliability."""
    spec = SCENARIOS[scenario]
    seed = f"{RECORD_SALT}|{truth}:{replicate}"
    rng = random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big"))
    records = []
    for origin, assumed in RELIABILITY.items():
        absent, correct, other = rng.random(), rng.random(), rng.randrange(7)
        if absent < spec["missing"]:
            continue
        claim = truth if correct < spec["actual"][origin] else [c for c in range(1, 9) if c != truth][other]
        records.append(Record(f"v2-{origin}", None if origin in spec["unknown"] else origin, claim, assumed))
    return records


def agreement_residual(dna, claim, assumed):
    """Observed DNA score of the claim minus its expectation under the assumed reliability."""
    if len(dna) != 8 or not 1 <= claim <= 8 or not 1 / 8 < assumed < 1:
        raise ValueError("Invalid residual input")
    expected = sum(p * (assumed * p + (1 - assumed) / 7 * (1 - p)) for p in dna)
    return dna[claim - 1] - expected


def origin_claims(records):
    """One (claim, assumed reliability) per known, internally consistent origin."""
    groups = defaultdict(set)
    for record in records:
        if record.origin in RELIABILITY:
            groups[record.origin].add((record.claimed_cousin, record.assumed_reliability))
    return {origin: next(iter(values)) for origin, values in groups.items() if len(values) == 1}


class Reference:
    def __init__(self, residuals):
        if len(residuals) < 2:
            raise ValueError("Reference needs at least two residuals")
        self.n = len(residuals)
        self.mean = sum(residuals) / self.n
        self.var = sum((r - self.mean) ** 2 for r in residuals) / (self.n - 1)
        if not self.var > 0:
            raise ValueError("Degenerate reference variance")

    def to_dict(self):
        return {"n": self.n, "mean": self.mean, "variance": self.var}


def reliability_check(residuals, reference):
    n = len(residuals)
    if n < MIN_RECORDS:
        return {"status": "insufficient_evidence", "n": n}
    mean = sum(residuals) / n
    z = (mean - reference.mean) / math.sqrt(reference.var / n + reference.var / reference.n)
    return {"status": "rejected" if z < -Z_CRITICAL else "consistent", "n": n, "z": z}


def route_batch(rows, references, dna_calibration, fusion_calibration):
    """rows: list of (dna_scores, records). Returns per-row (set, family, reason) and per-origin checks."""
    residuals = defaultdict(list)
    for dna, records in rows:
        for origin, (claim, assumed) in origin_claims(records).items():
            residuals[origin].append(agreement_residual(dna, claim, assumed))
    checks = {origin: reliability_check(residuals[origin], references[origin]) for origin in RELIABILITY}
    failed = sorted(o for o, c in checks.items() if c["status"] != "consistent")
    output = []
    for dna, records in rows:
        if failed and complete_bundle(records)[0]:
            reason = "reliability_" + "_".join(f"{o}_{checks[o]['status']}" for o in failed)
            output.append((checked_set(Scores("dna_only", tuple(dna)), dna_calibration), "dna_only", reason))
        else:
            output.append(corrected_prediction(dna, records, dna_calibration, fusion_calibration))
    return output, checks


def batch_order(n):
    order = list(range(n))
    random.Random(int.from_bytes(hashlib.sha256(BATCH_SALT.encode()).digest()[:8], "big")).shuffle(order)
    return order


def batches(n, size):
    order = batch_order(n)
    step = n if size == "all" else size
    return [order[i:i + step] for i in range(0, n, step)]


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUT / "frozen_protocol.json"
    if protocol_path.exists():
        raise ValueError("Protocol already frozen; existing v3 artifacts will not be overwritten")
    v2_protocol = json.loads((V2_OUT / "frozen_protocol.json").read_text())
    protocol = {
        "version": 3, "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Label-free, source-level reliability check before fusion. No new DNA model, data, app integration or AI.",
        "design_disclosure": "Designed after the v2 incorrect_A45_complete failure was observed on these same evaluation rows. Four new scenarios (seen_before_design=false) were fixed here before any v3 result existed.",
        "historical_exposure": v2_protocol["historical_exposure"],
        "split": "Reuses the frozen v2 split unchanged (v2_calibration batch1 calibrates/references; v2_evaluation batch2 evaluates).",
        "reference": "Per-origin residual mean/variance from v2-calibration rows with v2 nominal_missing25 records whose actual reliability equals the assumed reliability.",
        "residual": "DNA score of claimed degree minus sum_c s(c)*(r*s(c)+(1-r)/7*(1-s(c))) with r the assumed reliability and s the DNA-only scores.",
        "test": {"type": "one-sided z on batch mean residual vs reference", "alpha_per_origin": ALPHA_PER_ORIGIN, "z_critical": Z_CRITICAL, "min_records_per_origin": MIN_RECORDS},
        "routing": "If any origin is rejected or has fewer than the minimum records in the batch, rows that would fuse instead use DNA scores with DNA calibration. Other rows follow v2 routing.",
        "batching": {"sizes": list(BATCH_SIZES), "salt": BATCH_SALT, "rule": "One frozen shuffle of evaluation rows, chunked; final partial batch kept."},
        "record_seed_salt": RECORD_SALT, "nominal_coverage": 0.9, "assumed_reliabilities": RELIABILITY, "scenarios": SCENARIOS,
        "comparators": ["dna_only", "v2_corrected_no_check"] + [f"v3_checked_batch_{s}" for s in BATCH_SIZES],
        "calibration_rule": "Thresholds recomputed with the v2 procedure on v2-calibration rows and required to equal those saved in v2 comparison.json.",
        "v2_split_sha256": v2_protocol["split_sha256"], "v2_protocol_sha256": digest(V2_OUT / "frozen_protocol.json"),
        "v2_comparison_sha256": digest(V2_OUT / "comparison.json"), "v2_implementation_sha256": digest(ROOT / "version2.py"),
        "source_manifest_sha256": digest(ROOT / "cache/data_manifest.json"), "dna_models_sha256": digest(ROOT / "results/models.json"),
        "implementation_sha256": digest(__file__),
        "claims_limit": "Fabricated records with invented reliabilities; batch-level check needs many cases per source; prototype only, not validated forensic calibration or novel genetics.",
    }
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf8")
    (OUT / "frozen_protocol.sha256").write_text(digest(protocol_path) + "\n", encoding="ascii")
    print(json.dumps({"frozen_protocol_sha256": digest(protocol_path), "evaluation_not_yet_run": True}))


def evaluate():
    started = time.monotonic()
    protocol_path = OUT / "frozen_protocol.json"
    if (OUT / "comparison.json").exists():
        raise ValueError("Evaluation already saved; refusing to overwrite results")
    protocol = json.loads(protocol_path.read_text())
    if digest(protocol_path) != (OUT / "frozen_protocol.sha256").read_text().strip():
        raise ValueError("Frozen protocol was modified")
    checks = [(Path(__file__), "implementation_sha256"), (ROOT / "version2.py", "v2_implementation_sha256"), (V2_OUT / "comparison.json", "v2_comparison_sha256"),
              (V2_OUT / "frozen_protocol.json", "v2_protocol_sha256"), (ROOT / "cache/data_manifest.json", "source_manifest_sha256"), (ROOT / "results/models.json", "dna_models_sha256")]
    for path, key in checks:
        if digest(path) != protocol[key]:
            raise ValueError(f"Frozen artifact differs ({key}); evaluation refused")
    manifest = json.loads((ROOT / "cache/data_manifest.json").read_text())
    entries = {(e["model"], e["batch"], e["cousin_number"]): e for e in manifest["files"]}
    dna = HistogramModel.from_dict(json.loads((ROOT / "results/models.json").read_text())["models"]["cm_segments_positive_only"])

    cal_dna = [[] for _ in range(8)]; cal_complete = [[] for _ in range(8)]
    reference_residuals = defaultdict(list); calibration_groups = set()
    for cousin in range(1, 9):
        entry = entries[("ss_intf", 1, cousin)]
        for replicate, cm, segments in load_summary(ROOT / entry["path"], cousin, entry["sha256"]).records():
            if cm <= 0 or partition_v2(cousin, replicate) != "v2_calibration":
                continue
            calibration_groups.add((cousin, replicate))
            base = dna.scores(cm, segments)
            records = scenario_records(cousin, replicate, "nominal_missing25")
            cal_dna[cousin - 1].append(1 - base[cousin - 1])
            if complete_bundle(records)[0]:
                cal_complete[cousin - 1].append(1 - fused_scores(base, records, grouped=True)[cousin - 1])
            for origin, (claim, assumed) in origin_claims(records).items():
                reference_residuals[origin].append(agreement_residual(base, claim, assumed))
    calibrations = {}
    for name, values in [("dna_only", cal_dna), ("complete_known_fusion", cal_complete)]:
        model = HistogramModel(); model.calibrate(values, protocol["nominal_coverage"])
        calibrations[name] = Calibration(name, tuple(model.thresholds))
    saved = json.loads((V2_OUT / "comparison.json").read_text())["calibrations"]
    for name, calibration in calibrations.items():
        if safe_json(list(calibration.thresholds)) != saved[name]["thresholds"]:
            raise ValueError(f"Recomputed {name} thresholds differ from v2")
    references = {origin: Reference(reference_residuals[origin]) for origin in RELIABILITY}

    rows = []
    for cousin in range(1, 9):
        entry = entries[("ss_intf", 2, cousin)]
        for replicate, cm, segments in load_summary(ROOT / entry["path"], cousin, entry["sha256"]).records():
            if cm <= 0 or partition_v2(cousin, replicate) != "v2_evaluation":
                continue
            if (cousin, replicate) in calibration_groups or group_partition(cousin, replicate) != "calibration":
                raise ValueError("Held-out group leakage")
            rows.append((cousin, replicate, dna.scores(cm, segments)))
    rows_hash = hashlib.sha256("".join(f"{c},{r}\n" for c, r, _ in rows).encode()).hexdigest()

    report_scenarios = {}
    for scenario in SCENARIOS:
        records = [scenario_records(c, r, scenario) for c, r, _ in rows]
        metrics = {name: Metrics() for name in protocol["comparators"]}
        dna_sets = []
        for (cousin, _, base), recs in zip(rows, records):
            dna_set = checked_set(Scores("dna_only", base), calibrations["dna_only"])
            dna_sets.append(dna_set)
            metrics["dna_only"].add(cousin, dna_set)
            metrics["v2_corrected_no_check"].add(cousin, corrected_prediction(base, recs, calibrations["dna_only"], calibrations["complete_known_fusion"])[0])
        batch_stats = {}
        for size in BATCH_SIZES:
            name = f"v3_checked_batch_{size}"
            stats = {"batches": 0, "fusion_disabled_batches": 0, "per_origin": {o: {"rejected": 0, "insufficient_evidence": 0, "consistent": 0} for o in RELIABILITY},
                     "fallback_rows": 0, "fallback_set_disagreements_with_dna": 0, "z_values_all_batch": None}
            for indices in batches(len(rows), size):
                routed, origin_checks = route_batch([(rows[i][2], records[i]) for i in indices], references, calibrations["dna_only"], calibrations["complete_known_fusion"])
                stats["batches"] += 1
                stats["fusion_disabled_batches"] += any(c["status"] != "consistent" for c in origin_checks.values())
                for origin, check in origin_checks.items():
                    stats["per_origin"][origin][check["status"]] += 1
                if size == "all":
                    stats["z_values_all_batch"] = {o: c.get("z") for o, c in origin_checks.items()}
                for i, (hypotheses, family, _) in zip(indices, routed):
                    metrics[name].add(rows[i][0], hypotheses)
                    if family == "dna_only":
                        stats["fallback_rows"] += 1
                        stats["fallback_set_disagreements_with_dna"] += hypotheses != dna_sets[i]
            batch_stats[str(size)] = stats
        report_scenarios[scenario] = {"spec": SCENARIOS[scenario], "metrics": {k: m.report() for k, m in metrics.items()}, "batch_checks": batch_stats}

    report = {"version": 3, "protocol_sha256": digest(protocol_path), "evaluation_rows_sha256": rows_hash, "independent_fresh_source_data_claimed": False,
              "design_disclosure": protocol["design_disclosure"], "historical_exposure": protocol["historical_exposure"],
              "split_integrity": {"positive_calibration_groups": len(calibration_groups), "positive_evaluation_groups": len(rows), "overlap": 0},
              "references": {o: r.to_dict() for o, r in references.items()}, "z_critical": Z_CRITICAL,
              "calibrations_match_v2": True, "scenarios": report_scenarios, "runtime_seconds": time.monotonic() - started,
              "limits": ["Batch-level check: a single case or a source cited by few cases cannot be checked and falls back to DNA-only.",
                         "Detects sources worse than assumed in aggregate; does not estimate a corrected reliability or detect case-specific errors.",
                         "Reference assumes evaluation cases resemble calibration cases; a different case mix can shift residuals.",
                         "Fabricated records, invented reliabilities, simulation-only DNA, reused data; designed after seeing the v2 failure."]}
    (OUT / "comparison.json").write_text(json.dumps(safe_json(report), indent=2, allow_nan=False), encoding="utf8")
    for scenario, values in report_scenarios.items():
        print(scenario)
        for method, metric in values["metrics"].items():
            o = metric["overall"]
            print(f"  {method:28s} cov={o['set_coverage']:.4f} size={o['mean_set_size']:.3f} empty={o['empty_set_rate']:.4f}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["freeze", "evaluate"])
    action = parser.parse_args().action
    freeze() if action == "freeze" else evaluate()
