"""DNA consistency check and verified AI extraction (offline: the model is a fake client)."""
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from backend.dna import check, fitting_relationships, relationship
from backend.engine import derive
from backend.extraction import ExtractedClaim, ExtractionBatch, extract_document, review, verify
from backend.main import create_app
from backend.models import validate_citation
from backend.repository import JsonRepository, demo_state

EXAMPLES = Path(__file__).resolve().parents[2] / "data" / "examples"
OBITUARY = (EXAMPLES / "synthetic-hale-obituary.txt").read_text(encoding="utf8")
BIRTHS = (EXAMPLES / "synthetic-hale-birth-announcement.txt").read_text(encoding="utf8")


def claim(kind, person, quote, start, end=None, other=None, year=None, place=None):
    return ExtractedClaim(kind=kind, person=person, other_person=other, year=year, place=place, quote=quote, start_line=start, end_line=end or start)


OBITUARY_CLAIMS = [
    claim("death", "Frances Hale", "Frances Mercer Hale, 88, of Trenton, New Jersey, died peacefully at home on March 3, 2008.", 5, year=2008),
    claim("birth", "Frances Hale", "Born in 1920 in Trenton, Frances was the daughter of the late", 6, year=1920, place="Trenton, New Jersey"),
    claim("parent", "Walter Mercer", "Frances was the daughter of the late\nWalter and Mary Mercer.", 6, 7, other="Frances Hale"),
    claim("parent", "Mary Mercer", "Frances was the daughter of the late\nWalter and Mary Mercer.", 6, 7, other="Frances Hale"),
    claim("spouse", "Frances Hale", "Frances was predeceased by her husband of 51 years, Edward Hale", 10, other="Edward Hale"),
    claim("sibling", "Frances Hale", "Frances was predeceased by her husband of 51 years, Edward Hale, and by\nher brother, Arthur Mercer.", 10, 11, other="Arthur Mercer"),
    claim("parent", "Frances Hale", "Frances is survived by her son, George Hale", 13, other="George Hale"),
    claim("spouse", "George Hale", "George Hale, and his wife Patricia", 13, other="Patricia Hale"),
    # Two typical model mistakes that must be rejected:
    claim("parent", "Frances Hale", "and by her beloved granddaughter, Lena Hale.", 14, other="Lena Hale"),  # grandparent read as parent
    claim("birth", "Lena Hale", "and by her beloved granddaughter, Lena Hale.", 14, year=1972),  # year not in this record
]
_B = BIRTHS.split("\n")
BIRTH_CLAIMS = [
    claim("birth", "Lena Hale", "a daughter, Lena Hale, born June 4, 1972,", 5, year=1972, place="Camden, New Jersey"),
    claim("parent", "George Hale", _B[3] + "\n" + "the birth of their first child, a daughter, Lena Hale", 4, 5, other="Lena Hale"),
    claim("parent", "Patricia Hale", "\n".join(_B[3:6]), 4, 6, other="Lena Hale"),
]


class FakeExtractor:
    name, model = "gemini", "fake-model-for-tests"

    def __init__(self):
        self.calls = 0

    def propose(self, text, known_names):
        self.calls += 1
        return ExtractionBatch(claims=BIRTH_CLAIMS if "Births" in text else OBITUARY_CLAIMS)


class BrokenExtractor:
    name, model = "gemini", "broken"

    def propose(self, text, known_names):
        raise RuntimeError("secret request details that must not leak")


def reviewed_demo():
    state = demo_state()
    for d in state["documents"]:
        d["processed"] = True
    return state


# --- DNA ---------------------------------------------------------------------------------------

def test_relationship_finds_closest_common_ancestors_and_half_relations():
    parents = {"ruth": {"arthur", "edith"}, "thomas": {"arthur", "edith"}, "clara": {"thomas", "alice"}}
    niece = relationship("ruth", "clara", parents)
    assert niece["generations"] == (1, 2) and not niece["half"] and niece["key"] == "aunt_niece"
    parents["half"] = {"arthur", "someone"}
    assert relationship("ruth", "half", parents)["key"] == "half_sibling"
    assert relationship("ruth", "stranger", parents) is None


def test_shared_cm_check_against_reference_ranges():
    parents = {"ruth": {"arthur", "edith"}, "thomas": {"arthur", "edith"}, "clara": {"thomas", "alice"}}
    related = relationship("ruth", "clara", parents)
    assert check(220, related)["status"] == "inconsistent"
    assert check(1700, related)["status"] == "consistent"
    assert check(220, None)["status"] == "unchecked"
    assert fitting_relationships(220)
    assert not any(label.casefold().startswith("aunt") for label in fitting_relationships(220))


def test_demo_case_every_recorded_lead_fails_dna_and_suggests_a_branch_search():
    result = derive(reviewed_demo())
    assert result["metrics"]["remaining_candidates"] == 0
    for c in result["candidates"]:
        assert c["status"] == "excluded"
        assert [d["status"] for d in c["dna_checks"]] == ["inconsistent"]
    action = result["next_actions"][0]
    assert action["id"] == "dna-branch-search" and "220" in action["title"]
    assert {"arthur", "edith"} <= set(action["person_ids"])
    assert any(f["title"] == "DNA does not fit any recorded lead" for f in result["findings"])


def test_without_a_dna_match_leads_are_not_dna_checked():
    state = reviewed_demo()
    state["documents"] = [d for d in state["documents"] if d["id"] != "d02"]
    result = derive(state)
    assert all(d["status"] == "unchecked" for c in result["candidates"] for d in c["dna_checks"])
    assert not any(a["id"] == "dna-branch-search" for a in result["next_actions"])


# --- extraction verification ---------------------------------------------------------------------

def test_verifier_accepts_supported_claims_and_rejects_unsupported_ones():
    document = {"id": "doc", "text": OBITUARY}
    accepted, rejected = review(ExtractionBatch(claims=OBITUARY_CLAIMS), document)
    assert len(accepted) == 8 and len(rejected) == 2
    reasons = " | ".join(r["reason"] for r in rejected)
    assert '"Frances" does not appear in the quote' in reasons
    assert "year 1972 does not appear in the quote" in reasons
    for item in accepted:
        assert validate_citation(item["citation"], [{**document, "processed": True}])


@pytest.mark.parametrize("bad,reason", [
    (claim("parent", "Walter Mercer", "Walter and Mary Mercer were proud parents", 7, other="Frances Hale"), "not in the cited lines"),
    (claim("birth", "Frances Hale", "Born in 1920 in Trenton, Frances", 6, year=1921), "year 1921"),
    (claim("sibling", "Frances Hale", "Frances was predeceased by her husband of 51 years, Edward Hale", 10, other="Edward Hale"), "no wording that supports a sibling"),
    (claim("parent", "Frances Hale", "Frances is survived", 13), "names only one person"),
    (claim("death", "Frances Hale", "x" * 10, 1, 9, year=2008), "more than 4 lines"),
    (claim("death", "Frances Hale", "died", 90, year=2008), "do not exist"),
])
def test_verifier_rejection_reasons(bad, reason):
    citation, why = verify(bad, OBITUARY)
    assert citation is None and reason in why


def test_whitespace_only_differences_cite_the_exact_lines():
    loose = claim("parent", "Walter Mercer", "Frances was the daughter of the late Walter and Mary Mercer.", 6, 7, other="Frances Hale")
    citation, _ = verify(loose, OBITUARY)
    assert citation["quote"] == "\n".join(OBITUARY.split("\n")[5:7])


def test_live_run_is_recorded_and_replayed_with_reverification(tmp_path):
    document = {"id": "upload-1", "name": "obit.txt", "text": OBITUARY}
    live = extract_document(document, [], FakeExtractor(), cache_dir=tmp_path)
    assert live["source"] == "live" and live["proposed"] == 10 and len(live["accepted"]) == 8
    replay = extract_document(document, [], None, cache_dir=tmp_path)
    assert replay["source"] == "replay" and replay["accepted"] == live["accepted"] and replay["recorded_at"] == live["recorded_at"]
    assert extract_document({**document, "text": OBITUARY + " "}, [], None, cache_dir=tmp_path) is None  # changed text: no replay
    failed = extract_document(document, [], BrokenExtractor(), cache_dir=tmp_path)
    assert failed["source"] == "failed" and "secret" not in failed["note"]


# --- end to end: the twist ---------------------------------------------------------------------

def test_ai_read_records_reveal_a_branch_that_fits_the_dna(tmp_path, monkeypatch):
    import backend.extraction as extraction
    monkeypatch.setattr(extraction, "CACHE", tmp_path / "cache")
    fake = FakeExtractor()
    with TestClient(create_app(JsonRepository(tmp_path / "store"), provider=None, extractor=fake)) as client:
        client.post("/api/cases/demo", json={})
        before = client.post("/api/cases/demo-case/investigate", json={}).json()
        assert before["metrics"]["remaining_candidates"] == 0
        client.post("/api/cases/demo-case/documents", json={"name": "Hale obituary.txt", "text": OBITUARY})
        client.post("/api/cases/demo-case/documents", json={"name": "Hale birth announcement.txt", "text": BIRTHS})
        result = client.post("/api/cases/demo-case/investigate", json={}).json()
    assert fake.calls == 2
    lena = next(p for p in result["people"] if p["name"] == "Lena Hale")
    lead = next(c for c in result["candidates"] if c["person_id"] == lena["id"])
    assert lead["status"] == "possible" and lead["proposed_by_engine"]
    dna = lead["dna_checks"][0]
    assert dna["status"] == "consistent" and dna["expected_low_cm"] <= 220 <= dna["expected_high_cm"]
    assert all(validate_citation(c, result["documents"]) for c in lead["citations"])
    assert all(c["status"] == "excluded" for c in result["candidates"] if c["person_id"] != lena["id"])
    rejected = [f for f in result["findings"] if f["kind"] == "ai_rejected"]
    assert len(rejected) == 2 and all(f["citations"] for f in rejected)
    assert all(validate_citation(c, result["documents"]) for f in result["findings"] for c in f["citations"])
    assert any(f["kind"] == "ai_extraction" and "8 claims verified" in f["title"] for f in result["findings"])
    assert any(e["action"] == "ai_extraction" for e in result["audit"])
    assert not any(a["id"] == "dna-branch-search" for a in result["next_actions"])


# --- the schema actually sent to Gemini -------------------------------------------------------

def test_gemini_schema_uses_only_the_openapi_subset_gemini_accepts():
    """Regression: strict Pydantic schemas sent as-is got 400 INVALID_ARGUMENT from the live API."""
    import json
    from backend.gemini_schema import gemini_schema
    from backend.providers import ObservationBatch
    allowed = {"type", "properties", "required", "items", "enum", "description", "nullable", "minimum", "maximum", "format"}

    def keywords(node):  # schema keywords at every level, skipping user-defined property names
        yield from node.keys()
        for sub in node.get("properties", {}).values():
            yield from keywords(sub)
        if "items" in node:
            yield from keywords(node["items"])

    for model in (ExtractionBatch, ObservationBatch):
        assert set(keywords(gemini_schema(model))) <= allowed, model.__name__
        assert "$ref" not in json.dumps(gemini_schema(model))
    claim_schema = gemini_schema(ExtractionBatch)["properties"]["claims"]["items"]
    assert claim_schema["properties"]["other_person"] == {"type": "string", "nullable": True}
    assert claim_schema["properties"]["kind"]["enum"] == ["birth", "death", "alive", "parent", "spouse", "sibling"]
    assert set(claim_schema["required"]) >= {"kind", "person", "quote", "start_line", "end_line"}
