"""Lead timeline (issue #3). The node subprocess is mocked except in the preview test, which runs the real
blockchain/anchor.mjs offline (preview mode reads no key and makes no network call)."""
import json
from pathlib import Path
import subprocess
import pytest
from fastapi.testclient import TestClient
from backend import anchors
from backend.engine import derive
from backend.extraction import extract_document, raw_sha256
from backend.main import create_app
from backend.manifest import evidence_manifest
from backend.repository import JsonRepository

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "data" / "examples"
TX = "5" * 87


@pytest.fixture
def keypair(tmp_path, monkeypatch):
    path = tmp_path / "outside" / "dev.keypair.json"
    path.parent.mkdir()
    path.write_text(json.dumps(list(range(64))))  # never read: the subprocess is mocked
    monkeypatch.setenv("KINFOLD_SOLANA_KEYPAIR", str(path))
    return path


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(JsonRepository(tmp_path / "store"), provider=None, extractor=None)) as c:
        c.post("/api/cases/demo", json={})
        c.post("/api/cases/demo-case/investigate", json={"question": "", "max_steps": 3})
        yield c


def fake_node(calls, *, verify_ok=True, send_code=0, status="confirmed"):
    """Stands in for anchor.mjs: writes a receipt for the exact manifest digest it was given."""
    def run(args, timeout=150):
        calls.append(args)
        envelope = json.loads(Path(args[args.index("--manifest") + 1]).read_text(encoding="utf8"))
        memo = f"kinfold:v1:sha256:{envelope['digest']}"
        if "--send" in args:
            receipt = {"network": "solana-devnet", "status": status, "digest": envelope["digest"], "memo": memo,
                       "transaction": TX, "signer": "DevSigner1111", "slot": "123"}
            Path(args[args.index("--out") + 1]).write_text(json.dumps(receipt))
            return subprocess.CompletedProcess(args, send_code, json.dumps(receipt), "" if send_code == 0 else "Transaction failed. Receipt remains submitted.")
        if verify_ok:
            return subprocess.CompletedProcess(args, 0, json.dumps({"status": "verified_on_chain", "digest": envelope["digest"]}), "")
        return subprocess.CompletedProcess(args, 1, "", "Transaction is missing, unconfirmed, or failed. No verified anchor.")
    return run


def test_anchor_without_keypair_returns_setup_help_and_changes_nothing(client, monkeypatch):
    monkeypatch.delenv("KINFOLD_SOLANA_KEYPAIR", raising=False)
    monkeypatch.setattr(anchors, "run_node", lambda *a, **k: pytest.fail("must not run node without a keypair"))
    response = client.post("/api/cases/demo-case/anchor")
    assert response.status_code == 409 and "KINFOLD_SOLANA_KEYPAIR" in response.json()["detail"]
    assert client.get("/api/cases/demo-case").json()["anchors"] == []
    assert client.get("/api/cases/demo-case/manifest").json()["anchor"]["status"] == "not_anchored"


def test_keypair_inside_repository_is_refused(client, monkeypatch):
    monkeypatch.setenv("KINFOLD_SOLANA_KEYPAIR", str(ROOT / "package.json"))
    response = client.post("/api/cases/demo-case/anchor")
    assert response.status_code == 409 and "inside the repository" in response.json()["detail"]


def test_anchor_timeline_tracks_changes_and_reports_mismatch(client, keypair, monkeypatch):
    calls = []
    monkeypatch.setattr(anchors, "run_node", fake_node(calls))
    digest = client.get("/api/cases/demo-case/manifest").json()["digest"]
    first = client.post("/api/cases/demo-case/anchor").json()["anchors"]
    assert len(first) == 1 and first[0]["digest"] == digest and first[0]["matches_current"]
    assert first[0]["changes"] == ["First anchor for this case."] and "envelope" not in first[0]
    assert first[0]["explorer"] == f"https://explorer.solana.com/tx/{TX}?cluster=devnet"
    assert "does not prove the records are true" in first[0]["limits"]
    assert str(keypair) in calls[0] and "--send" in calls[0]
    manifest = client.get("/api/cases/demo-case/manifest").json()
    assert manifest["digest"] == digest  # the anchor is outside the manifest, so the digest is unchanged
    assert manifest["anchor"]["status"] == "anchored" and manifest["anchor"]["transaction"] == TX

    text = (EXAMPLES / "synthetic-hale-obituary.txt").read_text(encoding="utf8")
    client.post("/api/cases/demo-case/documents", json={"name": "obituary.txt", "text": text})
    after = client.get("/api/cases/demo-case").json()["anchors"][0]
    assert not after["matches_current"]
    assert client.get("/api/cases/demo-case/manifest").json()["anchor"]["status"] == "not_anchored"
    check = client.post("/api/cases/demo-case/anchors/1/verify").json()
    assert check["verified_on_chain"] and not check["current_matches_anchor"]

    second = client.post("/api/cases/demo-case/anchor").json()["anchors"]
    assert [a["number"] for a in second] == [1, 2] and "1 record(s) added" in second[1]["changes"]
    audit = client.get("/api/cases/demo-case").json()["audit"]
    assert sum(e["action"] == "anchored" for e in audit) == 2 and any(e["action"] == "anchor_verified" for e in audit)


def test_failed_or_unconfirmed_send_is_never_recorded(client, keypair, monkeypatch):
    monkeypatch.setattr(anchors, "run_node", fake_node([], send_code=1, status="submitted"))
    response = client.post("/api/cases/demo-case/anchor")
    assert response.status_code == 502
    assert TX in response.json()["detail"] and "Nothing is claimed on-chain" in response.json()["detail"]
    assert client.get("/api/cases/demo-case").json()["anchors"] == []
    assert client.get("/api/cases/demo-case/manifest").json()["anchor"]["status"] == "not_anchored"


def test_verify_reports_chain_failure(client, keypair, monkeypatch):
    monkeypatch.setattr(anchors, "run_node", fake_node([], verify_ok=False))
    client.post("/api/cases/demo-case/anchor")
    check = client.post("/api/cases/demo-case/anchors/1/verify").json()
    assert not check["verified_on_chain"] and "No verified anchor" in check["detail"] and check["current_matches_anchor"]
    assert client.post("/api/cases/demo-case/anchors/9/verify").status_code == 404


def test_node_missing_is_a_clean_error(client, keypair, monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError("node")
    monkeypatch.setattr(anchors, "run_node", missing)
    response = client.post("/api/cases/demo-case/anchor")
    assert response.status_code == 502 and "FileNotFoundError" in response.json()["detail"]


def hale_state(tmp_path):
    """Demo case with both Hale records extracted from the real recorded Gemini responses in data/ai_cache."""
    state = JsonRepository(tmp_path).reset_demo()
    for name in ("synthetic-hale-obituary.txt", "synthetic-hale-birth-announcement.txt"):
        document = {"id": "upload-" + name.removesuffix(".txt"), "name": name, "text": (EXAMPLES / name).read_text(encoding="utf8"), "kind": "uploaded_text", "synthetic": False, "processed": True}
        state["documents"].append(document)
        result = extract_document(document, [], extractor=None, cache_dir=ROOT / "data" / "ai_cache")
        assert result["source"] == "replay"
        state.setdefault("ai_extractions", {})[document["id"]] = result
    for d in state["documents"]:
        d["processed"] = True
    return state


def test_ai_raw_output_is_sealed_into_the_manifest(tmp_path):
    state = hale_state(tmp_path)
    import hashlib
    hale = {hashlib.sha256((EXAMPLES / n).read_text(encoding="utf8").encode("utf8")).hexdigest() for n in ("synthetic-hale-obituary.txt", "synthetic-hale-birth-announcement.txt")}
    entries = [json.loads(p.read_text(encoding="utf8")) for p in (ROOT / "data" / "ai_cache").glob("*.json")]
    recorded = {raw_sha256(e["raw"]) for e in entries if e.get("document_sha256") in hale}  # other recordings (e.g. the photo transcript) aren't in this state
    assert {r["raw_sha256"] for r in state["ai_extractions"].values()} == recorded
    manifest = evidence_manifest(derive(state))
    assert len(manifest["manifest"]["ai_recordings"]) == 2
    assert all(len(r["raw_sha256"]) == 64 and r["model"] == "gemini-3.5-flash" for r in manifest["manifest"]["ai_recordings"])
    # Editing what the AI said (even without changing which claims pass) changes the digest.
    tampered = json.loads(json.dumps(state))
    first = sorted(tampered["ai_extractions"])[0]
    tampered["ai_extractions"][first]["raw_sha256"] = raw_sha256({"claims": []})
    assert evidence_manifest(derive(tampered))["digest"] != manifest["digest"]


def test_real_anchor_script_accepts_the_api_manifest_offline(tmp_path):
    """Runs the real anchor.mjs in preview mode: no key, no network. Proves Python and JS agree on the digest."""
    envelope = evidence_manifest(derive(hale_state(tmp_path)))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf8")
    proc = anchors.run_node(["--manifest", str(path)], timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "not_anchored" and out["memo"] == f"kinfold:v1:sha256:{envelope['digest']}"
