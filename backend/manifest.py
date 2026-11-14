import hashlib
import json


def evidence_manifest(snapshot):
    # Audit timestamps and anchor metadata are deliberately not evidence content.
    manifest = {"schema_version": 1, "case": snapshot["case"],
                "people": sorted(snapshot["people"], key=lambda p: p["id"]),
                "documents": sorted(snapshot["documents"], key=lambda d: d["id"]),
                "relationships": sorted(snapshot["relationships"], key=lambda r: r["id"]),
                "findings": sorted(snapshot["findings"], key=lambda f: f["id"]),
                "candidates": sorted(snapshot["candidates"], key=lambda c: c["person_id"]),
                "ai_recordings": sorted(snapshot.get("ai_recordings", []), key=lambda r: r["document_id"])}
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf8")
    return {"case_id": snapshot["case"]["id"], "version": snapshot["case"]["version"], "algorithm": "sha256",
            "digest": hashlib.sha256(canonical).hexdigest(), "manifest": manifest,
            "anchor": {"status": "not_anchored", "network": "solana-devnet", "transaction": None}}
