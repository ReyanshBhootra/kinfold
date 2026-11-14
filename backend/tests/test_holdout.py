from scripts.evaluate import evaluate


def test_separate_families_and_conflicting_constraint_abstention():
    report = evaluate()
    assert report["passed"]
    assert len(report["cases"]) == 2
    assert sum(c["candidate_count"] for c in report["cases"]) == 6
    assert report["comparison"]["birth_range_only_correct"] == 4
    assert report["comparison"]["full_record_engine_correct"] == 6
