"""Tests for an explicitly fabricated record layer, not real-record effectiveness."""
import math
import pytest
from research.genetics.records import Record, fabricated_records, fused_scores, choose_verification, oracle_log_gain


def test_copy_lineage_invariance_and_naive_overcount_are_explicit():
    dna = (0.125,) * 8
    source = Record('original','source-A',2,0.85)
    copies = [Record(f'copy-{i}','source-A',2,0.85) for i in range(6)]
    assert fused_scores(dna,[source],True) == pytest.approx(fused_scores(dna,copies,True))
    assert fused_scores(dna,copies,False)[1] > fused_scores(dna,copies,True)[1]
    assert math.isclose(sum(fused_scores(dna,copies,False)),1)


def test_conflicting_known_origin_and_unknown_lineage_do_not_establish_independence():
    dna=(0.125,)*8
    conflicting=[Record('a','same',2,.85),Record('b','same',3,.85)]
    assert fused_scores(dna,conflicting,True) == pytest.approx(dna)
    unknown=[Record('a',None,2,.85)]*6
    assert fused_scores(dna,unknown,True) == pytest.approx(dna)
    assert fused_scores(dna,[],True) == pytest.approx(dna)


def test_generated_records_are_reproducible_and_copied_scenario_preserves_original_claims():
    for replicate in range(1,100):
        original=fabricated_records(4,replicate)
        copied=fabricated_records(4,replicate,'A_copied_six_times')
        assert original == fabricated_records(4,replicate)
        assert {(r.origin,r.claimed_cousin) for r in original} == {(r.origin,r.claimed_cousin) for r in copied}
        assert fused_scores((.125,)*8,original,True) == pytest.approx(fused_scores((.125,)*8,copied,True))


def test_verification_policy_uses_scores_only_and_evaluation_oracle_is_separate():
    scores=(.4,.1,.1,.1,.1,.1,.05,.05)
    records=[Record('a','A',1,.85),Record('b','B',2,.7)]
    chosen=choose_verification(scores,records)
    assert chosen.document_id == 'a'
    assert choose_verification(scores,[]) is None
    assert oracle_log_gain(scores,chosen,1) == pytest.approx(-math.log(.4))
    assert oracle_log_gain(scores,chosen,3) == pytest.approx(-math.log(.6))
    assert oracle_log_gain(scores,None,3) == 0


def test_invalid_stress_assumptions_are_rejected():
    with pytest.raises(ValueError):
        fused_scores((.125,)*8,[Record('x','A',9,.85)])
    with pytest.raises(ValueError):
        fused_scores((.125,)*8,[Record('x','A',1,1.0)])
