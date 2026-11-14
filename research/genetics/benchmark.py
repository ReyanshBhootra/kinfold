"""Reproducible standard-library baseline; no production-app imports or live models."""
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import time
from .baseline import HistogramModel
from .data import load_summary, partitions

ROOT = Path(__file__).resolve().parent


class Metrics:
    def __init__(self):
        self.n = self.correct = self.covered = self.singletons = self.singleton_correct = self.empty = self.set_size = self.zero = self.naive_correct = 0
        self.brier = 0.0
        self.confusion = [[0] * 8 for _ in range(8)]
        self.by_class = [{"n": 0, "correct": 0, "covered": 0, "set_size": 0, "singleton": 0} for _ in range(8)]
        self.set_sizes = Counter()

    def add(self, label, cm, scores, hypotheses):
        truth = label - 1
        top = max(range(8), key=lambda k: scores[k])
        covered = label in hypotheses
        self.n += 1; self.correct += top == truth; self.covered += covered
        self.singletons += len(hypotheses) == 1
        self.singleton_correct += len(hypotheses) == 1 and covered
        self.empty += not hypotheses; self.set_size += len(hypotheses); self.zero += cm == 0
        self.naive_correct += label == 1
        self.brier += sum((value - (i == truth)) ** 2 for i, value in enumerate(scores))
        self.confusion[truth][top] += 1; self.set_sizes[len(hypotheses)] += 1
        row = self.by_class[truth]; row["n"] += 1; row["correct"] += top == truth; row["covered"] += covered; row["set_size"] += len(hypotheses); row["singleton"] += len(hypotheses) == 1

    def report(self):
        divide = lambda a, b: a / b if b else None
        class_accuracy = [row["correct"] / row["n"] for row in self.by_class if row["n"]]
        return {"n": self.n, "top1_accuracy": divide(self.correct, self.n), "macro_average_class_accuracy": sum(class_accuracy) / len(class_accuracy) if class_accuracy else None, "prediction_set_coverage": divide(self.covered, self.n), "mean_set_size": divide(self.set_size, self.n),
                "single_degree_issued_fraction": divide(self.singletons, self.n), "single_degree_accuracy_when_issued": divide(self.singleton_correct, self.singletons),
                "abstention_fraction": 1 - self.singletons / self.n if self.n else None, "empty_set_fraction": divide(self.empty, self.n), "zero_sharing_fraction": divide(self.zero, self.n),
                "brier_score_uniform_simulation_prior": divide(self.brier, self.n), "chance_uniform_expected_accuracy": 0.125, "always_1C_accuracy": divide(self.naive_correct, self.n),
                "confusion_rows_true_columns_predicted_1C_to_8C": self.confusion, "set_size_counts": dict(sorted(self.set_sizes.items())),
                "per_class": [{"label": f"{i + 1}C", "n": row["n"], "top1_accuracy": divide(row["correct"], row["n"]), "set_coverage": divide(row["covered"], row["n"]), "mean_set_size": divide(row["set_size"], row["n"]), "singleton_fraction": divide(row["singleton"], row["n"])} for i, row in enumerate(self.by_class)]}


def run():
    started = time.monotonic()
    manifest_path = ROOT / "cache/data_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    if len(manifest["files"]) != 64:
        raise ValueError("Run the complete bounded summary download first")
    entries = {(f["model"], f["batch"], f["cousin_number"]): f for f in manifest["files"]}
    partition = partitions()
    output = ROOT / "results"; output.mkdir(exist_ok=True)
    split_csv = io.StringIO(newline="")
    writer = csv.writer(split_csv, lineterminator="\n"); writer.writerow(["cousin", "replicate", "group_partition"])
    split_counts = {}
    for cousin, groups in partition.items():
        split_counts[f"{cousin}C"] = dict(Counter(groups[1:]))
        for replicate in range(1, 50001):
            writer.writerow([cousin, replicate, groups[replicate]])
    split_bytes = gzip.compress(split_csv.getvalue().encode(), mtime=0)
    (output / "split_groups.csv.gz").write_bytes(split_bytes)

    methods = {"cm_unconditional": (HistogramModel(False), False), "cm_segments_unconditional": (HistogramModel(True), False),
               "cm_positive_only": (HistogramModel(False), True), "cm_segments_positive_only": (HistogramModel(True), True)}
    quality = []

    def source(model, batch, cousin):
        entry = entries[(model, batch, cousin)]
        summary = load_summary(ROOT / entry["path"], cousin, entry["sha256"])
        quality.append({"model": model, "batch": batch, "cousin": cousin, "source_rows": len(summary.observed) + len(summary.excluded), "positive_rows": summary.positive_rows,
                        "omitted_zeros_restored": summary.omitted_zero_pairs, "zero_pairs": summary.zero_pairs, "ibd2_positive_pairs": summary.ibd2_positive_pairs, "excluded_anomalies": summary.excluded})
        return summary

    primary_train = {c: source("ss_intf", 1, c) for c in range(1, 9)}
    for cousin, summary in primary_train.items():
        for replicate, cm, segments in summary.records():
            if partition[cousin][replicate] != "train":
                continue
            for estimator, positive_only in methods.values():
                if not positive_only or cm > 0:
                    estimator.fit_observation(cousin, cm, segments)
    calibration = {name: [[] for _ in range(8)] for name in methods}
    for cousin, summary in primary_train.items():
        for replicate, cm, segments in summary.records():
            if partition[cousin][replicate] != "calibration":
                continue
            for name, (estimator, positive_only) in methods.items():
                if not positive_only or cm > 0:
                    calibration[name][cousin - 1].append(1 - estimator.scores(cm, segments)[cousin - 1])
    for name, (estimator, _) in methods.items():
        estimator.calibrate(calibration[name], 0.9)
    model_file = {"schema_version": 1, "training_model": "ss_intf", "prior": "uniform within supported scope/cohort", "nominal_coverage": 0.9, "models": {name: model.to_dict() for name, (model, _) in methods.items()}}
    (output / "models.json").write_text(json.dumps(model_file, indent=2, allow_nan=False), encoding="utf8")
    evaluation = {}
    for model_name in ("ss_intf", "sa_intf", "ss_poiss", "sa_poiss"):
        metrics = {name: {"all_applicable": Metrics(), "positive_sharing": Metrics(), "zero_sharing": Metrics()} for name in methods}
        for cousin in range(1, 9):
            summary = source(model_name, 2, cousin)
            for replicate, cm, segments in summary.records():
                if partition[cousin][replicate] != "test":
                    continue
                for name, (estimator, positive_only) in methods.items():
                    if positive_only and cm == 0:
                        continue
                    scores = estimator.scores(cm, segments)
                    hypotheses = estimator.prediction_set(cm, segments)
                    metrics[name]["all_applicable"].add(cousin, cm, scores, hypotheses)
                    metrics[name]["positive_sharing" if cm > 0 else "zero_sharing"].add(cousin, cm, scores, hypotheses)
        evaluation[model_name] = {name: {cohort: value.report() for cohort, value in cohorts.items()} for name, cohorts in metrics.items()}
        print(json.dumps({"evaluated": model_name, "unconditional_n": evaluation[model_name]["cm_unconditional"]["all_applicable"]["n"]}), flush=True)

    used = {(q["model"], q["batch"], q["cousin"]) for q in quality}
    for model, batch, cousin in sorted(entries):
        if (model, batch, cousin) not in used:
            source(model, batch, cousin)  # QC every downloaded summary, including unused batches.
    report = {"report_schema_version": 1, "experiment": "Public Ped-sim full-cousin uncertainty baseline", "source_doi": "10.5281/zenodo.17489849",
              "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "experiment_config_sha256": hashlib.sha256((ROOT / "experiment_config.json").read_bytes()).hexdigest(),
              "split": {"definition": "Train/calibrate only ss_intf batch1 on disjoint hashed relationship/replicate groups; test batch2 of all models on the third disjoint group. Batch/model are excluded from group key. No random-row split.",
                        "group_counts": split_counts, "assignment_file": "split_groups.csv.gz", "assignment_sha256": hashlib.sha256(split_bytes).hexdigest(), "published_rng_seed_logs_available": False,
                        "independence_limit": "Ped-sim documents independent founder replicates, but archive seeds/logs are absent. Random-stream independence across runs is not certified. Matching replicate IDs stay together conservatively."},
              "methods": {name: {"training_count_by_class": model.totals, "calibration_count_by_class": [len(c) for c in calibration[name]], "nominal_class_conditional_coverage": 0.9,
                                "prior": "uniform over the eight supported cousin classes within the declared cohort", "abstention_rule": "issue one degree only when conformal set has exactly one member"} for name, (model, _) in methods.items()},
              "data_quality": quality, "evaluation": evaluation, "runtime_seconds": time.monotonic() - started,
              "limits": ["No unrelated, close non-cousin, half, removed, lineal, endogamy or genotyping-error hypotheses/controls.", "No real genotypes or people; source is simulated IBD output, not raw DNA.", "No detection threshold/sensitivity model for consumer DNA matching.", "Scores assume a uniform limited class prior; not population or forensic posterior probabilities.", "Conformal target relies on class-conditional exchangeability; crossover shift may violate it.", "Positive-only methods have small distant-cousin training/calibration counts; report per-class outcomes.", "Zero-sharing summaries restored from documented50000 slots and validated IDs, not treated as unrelated.", "No hyperparameters tuned on test outcomes; no novelty claim."]}
    (output / "benchmark.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({"report": str(output / "benchmark.json"), "runtime_seconds": report["runtime_seconds"]}), flush=True)
    return report


if __name__ == "__main__":
    run()
