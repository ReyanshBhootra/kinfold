"""Held-out synthetic correctness cases. Expected statuses are never runtime inputs."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.engine import derive, extract
from backend.models import validate_citation


def evaluate():
    fixture = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "heldout_cases.json"
    results = []
    baseline_correct, full_correct, decisions = 0, 0, 0
    for case in json.loads(fixture.read_text(encoding="utf8")):
        state = {"case": {"id": case["id"], "title": case["title"], "summary": "Held-out synthetic correctness case", "synthetic": True, "mode": "demo", "status": "reviewed", "version": 1},
                 "roster": case["people"], "documents": [{"id": f"record-{i}", "name": f"Synthetic record {i}", "kind": "evaluation", "text": text, "synthetic": True, "processed": True} for i, text in enumerate(case["records"])], "audit": []}
        snapshot = derive(state)
        observed = {c["person_id"]: c["status"] for c in snapshot["candidates"]}
        _, claims = extract(state)
        ranges = {c["value"] for c in claims if c["kind"] == "birth_range"}
        baseline = {}
        for person_id in case["expected"]:
            years = [c["value"] for c in claims if c["kind"] == "birth" and c["subject"] == person_id]
            outside = False
            if len(ranges) == 1 and years:
                low, high = map(int, next(iter(ranges)).split(":"))
                outside = all(not low <= year <= high for year in years)
            baseline[person_id] = "excluded" if outside else "retained"
            expected = "excluded" if case["expected"][person_id] == "excluded" else "retained"
            baseline_correct += baseline[person_id] == expected
            full_correct += ("excluded" if observed[person_id] == "excluded" else "retained") == expected
            decisions += 1
        citations = [c for item in snapshot["findings"] + snapshot["relationships"] + snapshot["candidates"] for c in item["citations"]]
        passed = observed == case["expected"] and snapshot["metrics"]["conflicts"] == case["expected_conflicts"] and all(validate_citation(c, snapshot["documents"]) for c in citations)
        results.append({"case": case["id"], "passed": passed, "candidate_count": len(observed), "observed": observed, "expected": case["expected"], "birth_range_only_baseline": baseline, "conflicts": snapshot["metrics"]["conflicts"], "citation_references_checked": len(citations)})
    return {"evaluation": "held-out synthetic deterministic correctness", "cases": results, "passed": all(r["passed"] for r in results), "comparison": {"decision": "retained versus excluded under fixture assumptions; needs_review counts as retained", "birth_range_only_correct": baseline_correct, "full_record_engine_correct": full_correct, "total": decisions, "baseline_definition": "Uses reviewed birth years and a nonconflicting birth range only; abstains on conflicting ranges and ignores life-status evidence."}, "limitations": "Two manually authored cases; not a scientific validation, genetic likelihood benchmark or real-person identification evaluation. No model training or calibration is claimed."}


if __name__ == "__main__":
    report = evaluate()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
