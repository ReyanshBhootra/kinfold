"""Record stress test performed only after the public-simulation baseline works."""
import hashlib
import json
import time
from pathlib import Path
from .baseline import HistogramModel
from .benchmark import Metrics
from .data import load_summary, partitions
from .records import fabricated_records, fused_scores, choose_verification, oracle_log_gain

ROOT = Path(__file__).resolve().parent
SCENARIOS = ["nominal_single_copy", "missing_70_percent", "A_copied_six_times", "A_wrong_rate_45_percent_copied_six_times", "A_copied_six_times_lineage_unknown"]


def run():
    started = time.monotonic()
    saved = json.loads((ROOT / "results/models.json").read_text())
    model = HistogramModel.from_dict(saved["models"]["cm_segments_positive_only"])
    manifest = json.loads((ROOT / "cache/data_manifest.json").read_text())
    entries = {(f["model"], f["batch"], f["cousin_number"]): f for f in manifest["files"]}
    groups = partitions(); calibration = [[] for _ in range(8)]; test = []
    for cousin in range(1, 9):
        for batch in (1, 2):
            entry = entries[("ss_intf", batch, cousin)]
            summary = load_summary(ROOT / entry["path"], cousin, entry["sha256"])
            if batch == 1:
                for replicate, cm, segments in summary.records():
                    if cm > 0 and groups[cousin][replicate] == "calibration":
                        scores = fused_scores(model.scores(cm, segments), fabricated_records(cousin, replicate), True)
                        calibration[cousin - 1].append(1 - scores[cousin - 1])
            else:
                eligible = [(replicate, cm, segments) for replicate, cm, segments in summary.records() if cm > 0 and groups[cousin][replicate] == "test"]
                eligible.sort(key=lambda row: hashlib.sha256(f"record-test-select|{cousin}:{row[0]}".encode()).digest())
                test += [(cousin, *row) for row in eligible[:1000]]
    calibrator = HistogramModel(); calibrator.calibrate(calibration, 0.9)
    results = {}
    for scenario in SCENARIOS:
        metrics = {name: Metrics() for name in ("dna_only", "naive_independent_documents", "provenance_grouped")}
        verification = {name: {"questions": 0, "selected_question_log_gain": 0.0, "first_available_log_gain": 0.0, "oracle_best_log_gain": 0.0} for name in ("naive_independent_documents", "provenance_grouped")}
        hard_covered = hard_empty = 0
        for truth, replicate, cm, segments in test:
            records = fabricated_records(truth, replicate, scenario)
            dna = model.scores(cm, segments); dna_set = model.prediction_set(cm, segments)
            metrics["dna_only"].add(truth, cm, dna, dna_set)
            hard = set(dna_set)
            for record in records:
                hard.intersection_update([record.claimed_cousin])
            hard_covered += truth in hard; hard_empty += not hard
            for name, grouped in [("naive_independent_documents", False), ("provenance_grouped", True)]:
                scores = fused_scores(dna, records, grouped)
                hypotheses = tuple(i + 1 for i, p in enumerate(scores) if 1 - p <= calibrator.thresholds[i])
                metrics[name].add(truth, cm, scores, hypotheses)
                chosen = choose_verification(scores, records, grouped)
                if chosen:
                    v = verification[name]; v["questions"] += 1
                    v["selected_question_log_gain"] += oracle_log_gain(scores, chosen, truth)
                    v["first_available_log_gain"] += oracle_log_gain(scores, records[0], truth)
                    v["oracle_best_log_gain"] += max(oracle_log_gain(scores, r, truth) for r in records)
        for record in verification.values():
            n = record["questions"]
            for field in ("selected_question_log_gain", "first_available_log_gain", "oracle_best_log_gain"):
                record[field + "_mean_nats"] = record.pop(field) / n if n else None
        results[scenario] = {"n": len(test), "metrics": {name: m.report() for name, m in metrics.items()}, "hard_record_intersection": {"true_degree_retention": hard_covered / len(test), "empty_set_fraction": hard_empty / len(test)}, "idealized_verification": verification}
    report = {"report_schema_version": 1, "experiment": "Explicitly fabricated fallible-record and copied-source sensitivity layer", "biological_or_historical_realism_claimed": False,
              "genetic_reference": "Public Ped-sim positive-sharing held-out features; model already trained on disjoint groups", "config_sha256": hashlib.sha256((ROOT / "record_stress_config.json").read_bytes()).hexdigest(),
              "genetic_models_sha256": hashlib.sha256((ROOT / "results/models.json").read_bytes()).hexdigest(), "calibration_counts": [len(x) for x in calibration],
              "fused_nominal_class_conditional_thresholds": calibrator.thresholds, "test_counts_by_class": {f"{c}C": sum(t[0] == c for t in test) for c in range(1, 9)},
              "scenarios": results, "runtime_seconds": time.monotonic() - started,
              "limits": ["Record reliabilities/error rates are invented stress parameters, not empirical estimates.", "Toy records directly state a cousin class; real genealogical records typically constrain ages/links indirectly.", "Copying lineage is supplied to the grouped method in known-lineage scenarios; unknown lineage is deliberately ignored for fusion.", "Fused models calibrate on nominal single-copy records only; shifted scenarios have no coverage guarantee.", "Verification oracle perfectly reveals claim correctness. This does not establish real-world next-record utility or optimality.", "Information-gain selection is existing methodology; no novelty claim.", "No extension has been connected to production Kinfold."]}
    (ROOT / "results/record_stress.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({scenario: {method: {k: value["all_applicable"][k] if "all_applicable" in value else value[k] for k in ["top1_accuracy", "prediction_set_coverage", "mean_set_size"]} for method, value in data["metrics"].items()} for scenario, data in results.items()}, indent=2))
    return report


if __name__ == "__main__":
    run()
