"""Bounded repair: a score vector must travel with its matching calibration.

V1 source/results are never overwritten. Freeze runs before evaluation features
are loaded. Newly scored rows are not claimed to be globally fresh source data.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import time
from .baseline import HistogramModel
from .data import group_partition, load_summary
from .records import Record, fused_scores

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/v2"
SCENARIOS = ("clean_complete", "nominal_missing25", "missing70", "incorrect_A45_complete", "unknown_all_complete", "unknown_A_complete")
RELIABILITY = {"A": 0.85, "B": 0.7}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def partition_v2(cousin, replicate):
    old = group_partition(cousin, replicate)
    if old == "train":
        return "frozen_dna_training"
    if old == "test":
        return "v1_test_excluded"
    key = f"kinfold-fallback-v2-split-20261114|{cousin}:{replicate}"
    bucket = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") % 2
    return "v2_calibration" if bucket == 0 else "v2_evaluation"


def safe_json(value):
    if isinstance(value, float) and math.isinf(value):
        return "infinity"
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    return value


@dataclass(frozen=True)
class Scores:
    family: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class Calibration:
    family: str
    thresholds: tuple[float, ...]


def checked_set(scores, calibration):
    if scores.family != calibration.family:
        raise ValueError("Score/calibration family mismatch")
    if len(scores.values) != 8 or len(calibration.thresholds) != 8:
        raise ValueError("Eight supported classes required")
    return tuple(i + 1 for i, p in enumerate(scores.values) if 1 - p <= calibration.thresholds[i])


def complete_bundle(records):
    if not records:
        return False, "no_records"
    if any(r.origin not in RELIABILITY for r in records):
        return False, "unknown_or_unsupported_origin"
    origins = defaultdict(list)
    for record in records:
        origins[record.origin].append(record)
    if set(origins) != set(RELIABILITY):
        return False, "missing_required_origin"
    for origin, values in origins.items():
        assertions = {(r.claimed_cousin, r.assumed_reliability) for r in values}
        if len(assertions) != 1:
            return False, "conflicting_origin_bundle"
        claim, reliability = next(iter(assertions))
        if claim not in range(1, 9) or reliability != RELIABILITY[origin]:
            return False, "unsupported_assertion_or_assumed_reliability"
    return True, "complete_known_consistent_origins"


def corrected_prediction(dna, records, dna_calibration, complete_calibration):
    eligible, reason = complete_bundle(records)
    if eligible:
        scores = Scores("complete_known_fusion", fused_scores(dna, records, grouped=True))
        calibration = complete_calibration
    else:
        scores = Scores("dna_only", tuple(dna))
        calibration = dna_calibration
    return checked_set(scores, calibration), scores.family, reason


def generated_records(truth, replicate, scenario):
    # A new, frozen record seed: no v1 generated record realization is reused.
    seed = f"kinfold-fallback-v2-records-20261114|{truth}:{replicate}"
    rng = random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big"))
    records = []
    missing = 0.25 if scenario == "nominal_missing25" else 0.7 if scenario == "missing70" else 0.0
    for origin, assumed in RELIABILITY.items():
        absent, correct, other = rng.random(), rng.random(), rng.randrange(7)
        actual = 0.55 if origin == "A" and scenario == "incorrect_A45_complete" else assumed
        if absent < missing:
            continue
        claim = truth if correct < actual else [c for c in range(1, 9) if c != truth][other]
        known = None if scenario == "unknown_all_complete" or (origin == "A" and scenario == "unknown_A_complete") else origin
        records.append(Record(f"v2-{origin}", known, claim, assumed))
    return records


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUT / "frozen_protocol.json"
    if protocol_path.exists():
        raise ValueError("Protocol already frozen; existing v2 artifacts will not be overwritten")
    snapshot = ROOT / "results/v1_preserved"
    snapshot.mkdir(exist_ok=True)
    preserved = {}
    for relative in ("results/benchmark.json", "results/record_stress.json", "results/models.json", "results/split_groups.csv.gz", "experiment_config.json", "record_stress_config.json", "FINDINGS.md"):
        source = ROOT / relative
        target = snapshot / Path(relative).name
        if target.exists() and digest(target) != digest(source):
            raise ValueError("Preserved v1 snapshot differs; refusing replacement")
        if not target.exists():
            shutil.copyfile(source, target)
        preserved[relative] = digest(source)
    rows = ["cousin,replicate,v1_partition,v2_partition\n"]
    counts = {}
    for cousin in range(1, 9):
        class_counts = Counter()
        for replicate in range(1, 50001):
            phase = partition_v2(cousin, replicate)
            class_counts[phase] += 1
            rows.append(f"{cousin},{replicate},{group_partition(cousin, replicate)},{phase}\n")
        counts[f"{cousin}C"] = dict(class_counts)
    split = gzip.compress("".join(rows).encode(), mtime=0)
    (OUT / "frozen_split.csv.gz").write_bytes(split)
    protocol = {
        "version": 2, "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Repair score/threshold routing only; no new genetic model, app integration or reliability estimator",
        "heldout_definition": "V1 calibration groups are deterministically divided into v2 calibration/evaluation; only batch1 calibrates, only batch2 evaluates. All matching IDs stay together across batches/models. Entire v1 test partition excluded.",
        "historical_exposure": "No wholly unused source groups remain. V2 evaluation batch2 rows were not previously scored, but their group IDs had batch1 counterparts in v1 calibration. Not independent fresh simulations or a globally untouched holdout.",
        "seed_independence": "Published source seed logs absent; independence not certified. Conservative ID grouping retained.",
        "split_salt": "kinfold-fallback-v2-split-20261114", "record_seed_salt": "kinfold-fallback-v2-records-20261114",
        "source": "ss_intf only; positive-sharing full1C–8C summaries", "dna_model": "Reuse v1 histogram counts trained only on v1 train groups; replace all calibration thresholds with v2 calibration",
        "nominal_coverage": 0.9, "assumed_reliabilities": RELIABILITY, "nominal_missing_probability": 0.25,
        "policy": "Use complete-bundle calibrated grouped fusion only when exactly A/B known, present, internally consistent and assumed reliabilities match. Otherwise route DNA scores together with DNA-calibrated thresholds. Unknown records are not partially fused.",
        "calibration": "DNA thresholds on every positive v2-cal row; legacy mixed thresholds on nominal25 missing records; complete-fusion thresholds only on complete nominal bundles. No test-driven threshold changes.",
        "comparators": ["v1_logic_recalibrated_on_v2_cal", "corrected_matching_fallback", "dna_only"], "scenarios": list(SCENARIOS),
        "evaluation_rule": "All positive-sharing v2-evaluation batch2 rows; no outcome-based exclusions/caps", "class_group_counts": counts,
        "split_sha256": hashlib.sha256(split).hexdigest(), "source_manifest_sha256": digest(ROOT / "cache/data_manifest.json"),
        "dna_models_sha256": digest(ROOT / "results/models.json"), "implementation_sha256": digest(__file__), "preserved_v1_sha256": preserved,
        "claims_limit": "Fabricated records with invented reliability; exploratory prototype repair, not novel genetics or validated forensic calibration"
    }
    protocol_path.write_text(json.dumps(protocol, indent=2), encoding="utf8")
    (OUT / "frozen_protocol.sha256").write_text(digest(protocol_path) + "\n", encoding="ascii")
    print(json.dumps({"frozen_protocol_sha256": digest(protocol_path), "split_sha256": protocol["split_sha256"], "evaluation_not_yet_run": True}))


class Metrics:
    def __init__(self):
        self.rows = [{"n": 0, "covered": 0, "total_set_size": 0, "abstained": 0, "empty": 0} for _ in range(8)]

    def add(self, truth, hypotheses):
        row = self.rows[truth - 1]
        row["n"] += 1; row["covered"] += truth in hypotheses
        row["total_set_size"] += len(hypotheses); row["abstained"] += len(hypotheses) != 1; row["empty"] += not hypotheses

    @staticmethod
    def rates(row):
        n = row["n"]
        return {**row, "set_coverage": row["covered"] / n if n else None, "false_exclusion_rate": (n - row["covered"]) / n if n else None,
                "mean_set_size": row["total_set_size"] / n if n else None, "abstention_rate": row["abstained"] / n if n else None, "empty_set_rate": row["empty"] / n if n else None}

    def report(self):
        total = {key: sum(row[key] for row in self.rows) for key in self.rows[0]}
        return {"overall": self.rates(total), "per_class": {f"{i + 1}C": self.rates(row) for i, row in enumerate(self.rows)}}


def evaluate():
    started = time.monotonic()
    protocol_path = OUT / "frozen_protocol.json"
    if (OUT / "comparison.json").exists():
        raise ValueError("Evaluation already saved; refusing to overwrite results")
    protocol = json.loads(protocol_path.read_text())
    if digest(protocol_path) != (OUT / "frozen_protocol.sha256").read_text().strip():
        raise ValueError("Frozen protocol was modified")
    for path, expected in [(OUT / "frozen_split.csv.gz", protocol["split_sha256"]), (ROOT / "cache/data_manifest.json", protocol["source_manifest_sha256"]), (ROOT / "results/models.json", protocol["dna_models_sha256"]), (Path(__file__), protocol["implementation_sha256"])]:
        if digest(path) != expected:
            raise ValueError("Frozen implementation/data/split differs; evaluation refused")
    manifest = json.loads((ROOT / "cache/data_manifest.json").read_text())
    entries = {(e["model"], e["batch"], e["cousin_number"]): e for e in manifest["files"]}
    dna = HistogramModel.from_dict(json.loads((ROOT / "results/models.json").read_text())["models"]["cm_segments_positive_only"])
    cal_dna = [[] for _ in range(8)]; cal_legacy = [[] for _ in range(8)]; cal_complete = [[] for _ in range(8)]
    group_ids = {"calibration": set(), "evaluation": set()}
    for cousin in range(1, 9):
        entry = entries[("ss_intf", 1, cousin)]
        summary = load_summary(ROOT / entry["path"], cousin, entry["sha256"])
        for replicate, cm, segments in summary.records():
            if cm <= 0 or partition_v2(cousin, replicate) != "v2_calibration":
                continue
            group_ids["calibration"].add((cousin, replicate))
            base = dna.scores(cm, segments); records = generated_records(cousin, replicate, "nominal_missing25")
            fused = fused_scores(base, records, grouped=True)
            cal_dna[cousin - 1].append(1 - base[cousin - 1]); cal_legacy[cousin - 1].append(1 - fused[cousin - 1])
            if complete_bundle(records)[0]:
                cal_complete[cousin - 1].append(1 - fused[cousin - 1])
    calibrations = {}
    for name, values in [("dna_only", cal_dna), ("legacy_nominal_mixture", cal_legacy), ("complete_known_fusion", cal_complete)]:
        temporary = HistogramModel(); temporary.calibrate(values, protocol["nominal_coverage"])
        calibrations[name] = Calibration(name, tuple(temporary.thresholds))
    results = {scenario: {method: Metrics() for method in protocol["comparators"]} for scenario in SCENARIOS}
    branches = {scenario: Counter() for scenario in SCENARIOS}
    fallback_equality = {scenario: {"fallback_rows": 0, "set_disagreements_with_dna": 0} for scenario in SCENARIOS}
    rows_hash = hashlib.sha256()
    for cousin in range(1, 9):
        entry = entries[("ss_intf", 2, cousin)]
        summary = load_summary(ROOT / entry["path"], cousin, entry["sha256"])
        for replicate, cm, segments in summary.records():
            if cm <= 0 or partition_v2(cousin, replicate) != "v2_evaluation":
                continue
            group = (cousin, replicate)
            if group in group_ids["calibration"] or group_partition(*group) != "calibration":
                raise ValueError("Held-out group leakage")
            group_ids["evaluation"].add(group)
            rows_hash.update(f"{cousin},{replicate},{cm:.12g},{segments}\n".encode())
            base = dna.scores(cm, segments)
            baseline_set = checked_set(Scores("dna_only", base), calibrations["dna_only"])
            for scenario in SCENARIOS:
                records = generated_records(cousin, replicate, scenario)
                # Intentionally reproduce v1's unchecked score/threshold logic as a comparator only.
                legacy_scores = fused_scores(base, records, grouped=True)
                legacy_set = tuple(i + 1 for i, p in enumerate(legacy_scores) if 1 - p <= calibrations["legacy_nominal_mixture"].thresholds[i])
                repaired, family, reason = corrected_prediction(base, records, calibrations["dna_only"], calibrations["complete_known_fusion"])
                results[scenario]["dna_only"].add(cousin, baseline_set)
                results[scenario]["v1_logic_recalibrated_on_v2_cal"].add(cousin, legacy_set)
                results[scenario]["corrected_matching_fallback"].add(cousin, repaired)
                branches[scenario][family + ":" + reason] += 1
                if family == "dna_only":
                    fallback_equality[scenario]["fallback_rows"] += 1
                    fallback_equality[scenario]["set_disagreements_with_dna"] += repaired != baseline_set
    if group_ids["calibration"] & group_ids["evaluation"]:
        raise ValueError("Calibration/evaluation overlap")
    for relative, expected in protocol["preserved_v1_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Version1 artifact changed during repair")
    report = {"version": 2, "protocol_sha256": digest(protocol_path), "evaluation_rows_sha256": rows_hash.hexdigest(),
              "historical_exposure": protocol["historical_exposure"], "independent_fresh_source_data_claimed": False,
              "split_integrity": {"positive_calibration_groups": len(group_ids["calibration"]), "positive_evaluation_groups": len(group_ids["evaluation"]), "overlap": 0, "v1_test_groups_used": 0, "v1_training_groups_evaluated": 0},
              "calibration_counts": {name: [len(x) for x in values] for name, values in [("dna_only", cal_dna), ("legacy_nominal_mixture", cal_legacy), ("complete_known_fusion", cal_complete)]},
              "calibrations": {name: {"family": c.family, "thresholds": c.thresholds} for name, c in calibrations.items()},
              "scenarios": {scenario: {"metrics": {method: metric.report() for method, metric in methods.items()}, "corrected_routes": dict(branches[scenario]), "fallback_dna_equality": fallback_equality[scenario]} for scenario, methods in results.items()},
              "v1_preservation_verified": True, "runtime_seconds": time.monotonic() - started,
              "limits": ["No globally untouched or independently seeded simulation groups available; newly evaluated batch2 rows have historical matching-group v1 calibration exposure.", "Fabricated records, direct cousin-label statements and invented reliability remain exploratory assumptions.", "Correction routes missing/unknown metadata conservatively, discarding partial record information; set size/abstention may increase.", "Incorrect reliability in otherwise complete known bundles is not detected or solved.", "Small distant-cousin calibration/test counts; no population/forensic validity, novelty or app integration claimed."]}
    (OUT / "comparison.json").write_text(json.dumps(safe_json(report), indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({scenario: {method: metric["overall"] for method, metric in values["metrics"].items()} for scenario, values in report["scenarios"].items()}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["freeze", "evaluate"])
    action = parser.parse_args().action
    freeze() if action == "freeze" else evaluate()
