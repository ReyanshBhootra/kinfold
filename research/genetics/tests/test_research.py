"""Fabricated schema fixtures below test plumbing only, never biological accuracy."""
import io
import math
import struct
import zipfile
import zlib
import pytest
from research.genetics.baseline import HistogramModel
from research.genetics.data import parse_tot, group_partition
from research.genetics.download import central_members, inflate_member, verify_definitions, RemoteZip

HEADER = "id IBD1 IBD2 total n_seg\n"


def test_strict_parser_restores_documented_zero_slots_without_fabricating_values():
    summary = parse_tot(HEADER + "2c1_g4-b1-i1 100 0 100 5\n2c50000_g4-b1-i1 20 0 20 1\n", 2)
    assert summary.positive_rows == 2 and summary.omitted_zero_pairs == 49998
    assert next(r for r in summary.records() if r[0] == 2) == (2, 0.0, 0)
    assert sum(1 for _ in summary.records()) == 50000
    assert summary.observed[50000] == (20, 1)


@pytest.mark.parametrize("row", ["2c1_g4-b1-i1 -1 0 -1 1", "2c1_g4-b1-i1 nan 0 nan 1", "2c50001_g4-b1-i1 20 0 20 1", "1c1_g3-b1-i1 20 0 20 1", "2c1_g4-b1-i1 10 1 10 1", "2c1_g4-b1-i1 10 0 10 1.5"])
def test_malformed_or_wrong_scope_rows_fail_closed(row):
    with pytest.raises(ValueError):
        parse_tot(HEADER + row + "\n", 2)


def test_duplicates_and_source_zero_anomaly_are_not_silently_imputed():
    row = "2c1_g4-b1-i1 20 0 20 1\n"
    with pytest.raises(ValueError, match="Duplicate"):
        parse_tot(HEADER + row + row, 2)
    summary = parse_tot(HEADER + "2c1_g4-b1-i1 0 0 0 1\n", 2)
    assert 1 in summary.excluded and 1 not in summary.observed
    assert summary.omitted_zero_pairs == 49999
    assert sum(1 for _ in summary.records()) == 49999


def test_whitespace_source_ibd2_only_fields_match_awk_schema():
    summary = parse_tot(HEADER + "2c1_g4-b1-i1  2.5 5 \n", 2)
    assert summary.observed[1] == (5, 0)


def test_split_has_no_matching_replicate_group_leakage_across_models_or_batches():
    groups = {name: set() for name in ["train", "calibration", "test"]}
    for cousin in range(1, 9):
        for replicate in range(1, 1001):
            group = (cousin, replicate)
            groups[group_partition(*group)].add(group)
            assert group_partition(*group) == group_partition(*group)
    assert not groups["train"] & groups["calibration"]
    assert not groups["train"] & groups["test"]
    assert not groups["calibration"] & groups["test"]
    assert sum(map(len, groups.values())) == 8000


def toy_model():
    model = HistogramModel(True)
    for label in range(1, 9):
        for _ in range(5):
            model.fit_observation(label, 10 * label, label)
    return model


def test_normalization_serialization_and_finite_sample_quantile():
    model = toy_model()
    assert math.isclose(sum(model.scores(20, 2)), 1)
    model.calibrate([[0.01, 0.02] for _ in range(8)], 0.9)
    assert all(math.isinf(q) for q in model.thresholds)  # ceil((2+1)*.9)>2
    assert len(model.prediction_set(20, 2)) == 8
    clone = HistogramModel.from_dict(model.to_dict())
    assert clone.scores(20, 2) == model.scores(20, 2)
    assert clone.prediction_set(20, 2) == model.prediction_set(20, 2)


def test_no_dna_sharing_does_not_become_unrelated_or_a_false_exact_degree():
    model = toy_model(); model.calibrate([[1.0] * 20 for _ in range(8)])
    result = model.predict(0, 0)
    assert result["abstain_from_single_degree"] is True
    assert all(label.endswith("C") for label in result["prediction_set"])
    assert "unrelated" not in result["simulation_reference_scores"]
    with pytest.raises(ValueError):
        model.feature(0, 3)


def test_zip_members_validate_crc_and_size_before_writing_source():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sim/deg3-full-b1.tot", HEADER + "1c1_g3-b1-i1 20 0 20 1\n")
    raw = stream.getvalue(); end = raw.rfind(b"PK\x05\x06")
    footer = struct.unpack_from("<4s4H2IH", raw, end)
    member = central_members(raw[footer[6]:footer[6] + footer[5]])[0]
    h = struct.unpack_from("<4s5H3I2H", raw, member.offset)
    start = member.offset + 30 + h[9] + h[10]
    data = raw[start:start + member.compressed]
    assert inflate_member(data, member).startswith(HEADER.encode())
    member.crc32 ^= 1
    with pytest.raises(ValueError, match="CRC"):
        inflate_member(data, member)


def test_zero_restoration_requires_documented_definition_counts():
    def archive(copies):
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:
            for cousin in range(1,9):
                z.writestr(f'deg{2*cousin+1}-full.def',f'def {cousin}c {copies} {cousin+2}\n')
            z.writestr('README.sh','50,000 pairs; omitted zeros50,001 - [line count of .tot file]')
        return output.getvalue()
    assert verify_definitions(archive(50000))['pairs_per_batch']==50000
    with pytest.raises(ValueError,match='copy count'):
        verify_definitions(archive(50001))


def test_range_downloader_refuses_ignored_range_without_reading_full_archive(monkeypatch):
    class Response:
        status=200
        headers={}
        def __enter__(self):return self
        def __exit__(self,*_args):pass
        def read(self,*_args):raise AssertionError('Full archive must never be read')
    monkeypatch.setattr('urllib.request.urlopen',lambda *_args,**_kwargs:Response())
    reader=object.__new__(RemoteZip);reader.url='https://example.invalid/file.zip?download=1';reader.size=1000;reader.budget=100;reader.received=0
    with pytest.raises(ValueError,match='full download refused'):
        reader.fetch(0,9)
    reader.budget=5
    with pytest.raises(ValueError,match='budget'):
        reader.fetch(0,9)
