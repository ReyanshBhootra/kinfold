"""Empirical histogram baselines and class-conditional split-conformal sets.

Normalized scores use a declared uniform eight-class simulation prior; they are
not validated population/posterior probabilities or an identity assessment.
"""
from collections import Counter
import math


class HistogramModel:
    def __init__(self, use_segments=False, alpha=0.1, width=0.18):
        self.use_segments, self.alpha, self.width = use_segments, alpha, width
        self.counts = [Counter() for _ in range(8)]
        self.totals = [0] * 8
        self.thresholds = None
        self._cache = {}

    def feature(self, cm, segments):
        if not math.isfinite(cm) or cm < 0 or segments < 0 or int(segments) != segments or (cm == 0 and segments != 0):
            raise ValueError("Invalid shared-cM/IBD1-segment input")
        cm_bin = 0 if cm == 0 else min(50, 1 + int(math.log1p(cm) / self.width))
        return (cm_bin, min(int(segments), 80)) if self.use_segments else (cm_bin,)

    def fit_observation(self, label, cm, segments):
        if not 1 <= label <= 8:
            raise ValueError("Unsupported cousin label")
        feature = self.feature(cm, segments)
        self.counts[label - 1][feature] += 1
        self.totals[label - 1] += 1
        self._cache.clear()

    def scores(self, cm, segments):
        feature = self.feature(cm, segments)
        if feature not in self._cache:
            if not all(self.totals):
                raise ValueError("All eight classes require training data")
            cells = 51 * 81 if self.use_segments else 51
            densities = [(self.counts[i][feature] + self.alpha) / (self.totals[i] + cells * self.alpha) for i in range(8)]
            total = sum(densities)
            self._cache[feature] = tuple(value / total for value in densities)
        return self._cache[feature]

    def calibrate(self, calibration_scores, coverage=0.9):
        if len(calibration_scores) != 8 or not 0 < coverage < 1:
            raise ValueError("Invalid calibration scope")
        self.thresholds = []
        for scores in calibration_scores:
            if not scores:
                raise ValueError("Each class requires calibration observations")
            scores = sorted(scores)
            rank = math.ceil((len(scores) + 1) * coverage)
            # Infinite threshold is the finite-sample rule when rank exceeds n.
            self.thresholds.append(scores[rank - 1] if rank <= len(scores) else float("inf"))

    def prediction_set(self, cm, segments):
        if self.thresholds is None:
            raise ValueError("Calibration required")
        scores = self.scores(cm, segments)
        return tuple(i + 1 for i, value in enumerate(scores) if 1 - value <= self.thresholds[i])

    def predict(self, cm, segments):
        scores = self.scores(cm, segments)
        hypotheses = self.prediction_set(cm, segments)
        return {"simulation_reference_scores": {f"{i + 1}C": value for i, value in enumerate(scores)}, "prediction_set": [f"{i}C" for i in hypotheses],
                "abstain_from_single_degree": len(hypotheses) != 1, "notice": "Restricted to simulated full1C–8C with a uniform class prior. No unrelated/half/removed/endogamy hypotheses. Not an identity or validated forensic probability."}

    def to_dict(self):
        return {"use_segments": self.use_segments, "alpha": self.alpha, "width": self.width, "totals": self.totals, "thresholds": self.thresholds,
                "counts": [{",".join(map(str, k)): v for k, v in counts.items()} for counts in self.counts]}

    @classmethod
    def from_dict(cls, data):
        model = cls(data["use_segments"], data["alpha"], data["width"])
        model.totals, model.thresholds = data["totals"], data["thresholds"]
        model.counts = [Counter({tuple(map(int, k.split(","))): v for k, v in counts.items()}) for counts in data["counts"]]
        return model
