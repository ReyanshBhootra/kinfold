"""Paper to proof: photographed records (offline: the vision model is a fake)."""
import base64
import hashlib
import json
from fastapi.testclient import TestClient
import pytest
from backend.main import create_app
from backend.models import validate_citation
from backend.photos import Transcription, TranscribedLine, cache_key, check
from backend.repository import JsonRepository
from backend.tests.test_dna_extraction import BIRTHS, OBITUARY, FakeExtractor

PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic test image bytes"
JPEG = b"\xff\xd8\xff\xe0" + b"another synthetic photo"


def b64(data):
    return base64.b64encode(data).decode()


def lines_for(text):
    return [TranscribedLine(text=line, box=[40 + 60 * i, 50, 90 + 60 * i, 950], uncertain=False) for i, line in enumerate(text.split("\n"))]


class FakeTranscriber:
    name, model = "gemini", "fake-vision-for-tests"

    def __init__(self, text=BIRTHS, bad_box=False):
        self.calls, self.text, self.bad_box = 0, text, bad_box

    def transcribe(self, data, media_type):
        self.calls += 1
        result = Transcription(lines=lines_for(self.text))
        if self.bad_box:
            result.lines[0].box = [900, 0, 100, 10]
        return check(result)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    import backend.extraction as extraction
    monkeypatch.setattr(extraction, "CACHE", tmp_path / "cache")
    return tmp_path / "cache"


def app(tmp_path, transcriber=None, extractor=None):
    return TestClient(create_app(JsonRepository(tmp_path / "store"), provider=None, extractor=extractor, agent=(None, None), transcriber=transcriber))


def add(client, data=PNG, media_type="image/png", name="Courier-Post clipping"):
    return client.post("/api/cases/demo-case/photos", json={"name": name, "media_type": media_type, "image_base64": b64(data), "capture": "webcam"})


def test_photo_is_hashed_on_arrival_stored_unchanged_and_deduplicated(tmp_path, cache):
    with app(tmp_path) as client:
        client.post("/api/cases/demo", json={})
        snap = add(client).json()
        photo = snap["photos"][0]
        assert photo["sha256"] == hashlib.sha256(PNG).hexdigest() and photo["status"] == "captured" and photo["bytes"] == len(PNG)
        image = client.get(f"/api/cases/demo-case/photos/{photo['id']}/image")
        assert image.content == PNG and image.headers["content-type"] == "image/png" and image.headers["x-content-sha256"] == photo["sha256"]
        assert len(add(client).json()["photos"]) == 1  # same bytes: same photo
        assert any(e["action"] == "photo_added" for e in snap["audit"])
        # an unconfirmed photo is not evidence yet: no record is added to the manifest
        assert "photo" not in json.dumps(client.get("/api/cases/demo-case/manifest").json()["manifest"]["documents"])


def test_stored_image_that_no_longer_matches_its_hash_is_refused(tmp_path, cache):
    with app(tmp_path) as client:
        client.post("/api/cases/demo", json={})
        photo = add(client).json()["photos"][0]
        (tmp_path / "store" / "blobs" / photo["sha256"]).write_bytes(PNG + b"edited")
        assert client.get(f"/api/cases/demo-case/photos/{photo['id']}/image").status_code == 409
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe").status_code == 409


@pytest.mark.parametrize("media_type, data, reason", [
    ("image/png", JPEG, "not a PNG"),
    ("image/gif", PNG, None),  # schema rejects the type
])
def test_wrong_or_unsupported_images_are_rejected(tmp_path, cache, media_type, data, reason):
    with app(tmp_path) as client:
        client.post("/api/cases/demo", json={})
        r = add(client, data=data, media_type=media_type)
        assert r.status_code == 422 and (reason is None or reason in r.json()["detail"])
        bad = client.post("/api/cases/demo-case/photos", json={"name": "x", "media_type": "image/png", "image_base64": "not base64!!"})
        assert bad.status_code == 422


def test_no_model_and_no_recording_means_no_transcription(tmp_path, cache):
    with app(tmp_path) as client:
        client.post("/api/cases/demo", json={})
        photo = add(client).json()["photos"][0]
        r = client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe")
        assert r.status_code == 409 and "no recorded transcription" in r.json()["detail"].lower()
        assert client.get("/api/cases/demo-case").json()["photos"][0]["transcription"] is None


def test_live_transcription_is_recorded_once_and_replayed_for_the_exact_bytes(tmp_path, cache):
    fake = FakeTranscriber()
    with app(tmp_path, transcriber=fake) as client:
        client.post("/api/cases/demo", json={})
        photo = add(client).json()["photos"][0]
        t = client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe").json()["photos"][0]["transcription"]
    assert t["source"] == "live" and fake.calls == 1 and [l["text"] for l in t["lines"]] == BIRTHS.split("\n")
    recording = cache / "transcriptions" / f"{cache_key(fake.model, photo['sha256'])}.json"
    assert json.loads(recording.read_text(encoding="utf8"))["image_sha256"] == photo["sha256"]
    with app(tmp_path / "second") as client:  # no model configured: replay of the recording
        client.post("/api/cases/demo", json={})
        again = add(client).json()["photos"][0]
        replay = client.post(f"/api/cases/demo-case/photos/{again['id']}/transcribe").json()["photos"][0]["transcription"]
        assert replay["source"] == "replay" and replay["lines"] == t["lines"] and replay["raw_sha256"] == t["raw_sha256"]
        other = add(client, data=PNG + b"one pixel different").json()["photos"][-1]
        assert client.post(f"/api/cases/demo-case/photos/{other['id']}/transcribe").status_code == 409  # different bytes, no replay


def test_invalid_model_output_and_invalid_recordings_are_never_used(tmp_path, cache):
    with app(tmp_path, transcriber=FakeTranscriber(bad_box=True)) as client:
        client.post("/api/cases/demo", json={})
        photo = add(client).json()["photos"][0]
        r = client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe")
        assert r.status_code == 409 and "Live transcription failed (ValueError)" in r.json()["detail"]
    target = cache / "transcriptions" / f"{cache_key('real-model', photo['sha256'])}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"model": "real-model", "prompt_version": "kinfold-transcribe-v1", "recorded_at": "2026-11-15T04:00:00Z",
                                  "image_sha256": photo["sha256"], "raw": {"lines": [{"text": "x", "box": [5, 5, 1, 1], "uncertain": False}]}}), encoding="utf8")
    with app(tmp_path) as client:
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe").status_code == 409


def test_confirm_keeps_one_entry_per_line_and_records_corrections(tmp_path, cache):
    with app(tmp_path, transcriber=FakeTranscriber(text="Lena Hale, born June 4, 1972,\nat C[?]per Hospital.")) as client:
        client.post("/api/cases/demo", json={})
        photo = add(client).json()["photos"][0]
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": ["a", "b"]}).status_code == 409  # not transcribed yet
        t = client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe").json()["photos"][0]["transcription"]
        assert t["lines"][1]["uncertain"] is True  # [?] always counts as uncertain
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": ["only one"]}).status_code == 422
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": ["a\nb", "c"]}).status_code == 422
        snap = client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": ["Lena Hale, born June 4, 1972,", "at Cooper Hospital."]}).json()
        assert client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": ["x", "y"]}).status_code == 409  # once only
    doc = next(d for d in snap["documents"] if d["id"] == snap["photos"][0]["document_id"])
    p = doc["provenance"]
    assert doc["kind"] == "photo_transcription" and not doc["processed"] and doc["text"] == "Lena Hale, born June 4, 1972,\nat Cooper Hospital."
    assert p["image_sha256"] == photo["sha256"] and p["text_sha256"] == hashlib.sha256(doc["text"].encode()).hexdigest()
    assert p["corrections"] == [{"line": 2, "from": "at C[?]per Hospital.", "to": "at Cooper Hospital."}]
    assert p["line_boxes"] == [l["box"] for l in t["lines"]] and p["transcription"]["raw_sha256"] == t["raw_sha256"]


def test_photographed_record_finds_lena_with_citations_back_to_the_photo(tmp_path, cache):
    extractor = FakeExtractor()
    with app(tmp_path, transcriber=FakeTranscriber(), extractor=extractor) as client:
        client.post("/api/cases/demo", json={})
        client.post("/api/cases/demo-case/investigate", json={})
        client.post("/api/cases/demo-case/documents", json={"name": "Hale obituary.txt", "text": OBITUARY})
        photo = add(client).json()["photos"][0]
        t = client.post(f"/api/cases/demo-case/photos/{photo['id']}/transcribe").json()["photos"][0]["transcription"]
        client.post(f"/api/cases/demo-case/photos/{photo['id']}/confirm", json={"lines": [l["text"] for l in t["lines"]]})
        result = client.post("/api/cases/demo-case/investigate", json={}).json()
        manifest = client.get("/api/cases/demo-case/manifest").json()
    assert extractor.calls == 2
    doc_id = result["photos"][0]["document_id"]
    lena = next(p for p in result["people"] if p["name"] == "Lena Hale")
    lead = next(c for c in result["candidates"] if c["person_id"] == lena["id"])
    assert lead["status"] == "possible" and lead["dna_checks"][0]["status"] == "consistent"
    from_photo = [c for c in lead["citations"] if c["document_id"] == doc_id]
    assert from_photo and all(validate_citation(c, result["documents"]) for c in from_photo)
    doc = next(d for d in result["documents"] if d["id"] == doc_id)
    boxes = doc["provenance"]["line_boxes"]
    assert all(c["end_line"] <= len(boxes) for c in from_photo)  # every cited line has a box on the photo
    sealed = next(d for d in manifest["manifest"]["documents"] if d["id"] == doc_id)
    assert sealed["provenance"]["image_sha256"] == photo["sha256"] and sealed["provenance"]["line_boxes"] == boxes


def test_photo_upload_body_limit_is_scoped_to_the_photo_endpoint(tmp_path, cache):
    with app(tmp_path) as client:
        client.post("/api/cases/demo", json={})
        big = "x" * 900_000
        assert client.post("/api/cases/demo-case/documents", json={"name": "big", "text": big}).status_code == 413
        r = client.post("/api/cases/demo-case/photos", json={"name": "big", "media_type": "image/png", "image_base64": b64(PNG + b"0" * 650_000)})
        assert r.status_code == 200
