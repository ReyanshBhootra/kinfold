# Initial API contract v0.1

Backend listens on http://127.0.0.1:8000. Frontend development server uses an /api proxy or configurable VITE_API_URL. Allow localhost development origins. JSON requests/responses; errors return {"detail":"human-readable explanation"}. IDs are strings. Timestamps ISO8601 UTC. Evidence documents remain untrusted data.

Propose contract changes in a GitHub issue; both owners agree before a PR changes it (see AGENTS.md).

## Endpoints
- GET /health -> {"status":"ok","mode":"demo"|"live","providers":{"gemini":false,"mongodb":false,"deepagents":false}}
- GET /api/cases -> {"cases":[{"id":"demo-case","title":"...","status":"...","synthetic":true}]}
- POST /api/cases/demo -> Snapshot (idempotently load/reset synthetic case; document reset semantics)
- GET /api/cases/{case_id} -> Snapshot
- POST /api/cases/{case_id}/investigate with {"question":"optional research question","max_steps":3} -> Snapshot. Initial synchronous endpoint is acceptable; frontend must show loading. Cap steps server-side.
- POST /api/cases/{case_id}/documents with {"name":"record.txt","text":"..."} -> Snapshot. Server enforces length bounds. No arbitrary file paths or URLs.
- GET /api/cases/{case_id}/manifest -> {"case_id":"...","version":1,"algorithm":"sha256","digest":"hex","manifest":{...},"anchor":{"status":"not_anchored","network":"solana-devnet","transaction":null}}
- POST /api/cases/{case_id}/verify with {"digest":"previous hex digest"} -> {"matches":true,"expected_digest":"...","actual_digest":"..."}

## Snapshot (fields required, arrays may be empty)
{
  "case": {"id":"demo-case","title":"...","summary":"...","status":"ready","synthetic":true,"mode":"demo","version":1},
  "people": [{"id":"p1","name":"Synthetic Person","birth_year":1960,"death_year":null,"locations":["..."],"candidate":true}],
  "relationships": [{"id":"r1","source":"p1","target":"p2","type":"parent","status":"supported","citations":[{"document_id":"d1","quote":"exact excerpt","start_line":1,"end_line":2}]}],
  "documents": [{"id":"d1","name":"...","text":"...","kind":"obituary","synthetic":true,"processed":false}],
  "findings": [{"id":"f1","kind":"relationship|conflict|exclusion|observation","title":"...","description":"...","severity":"info|warning","person_ids":["p1"],"citations":[]}],
  "candidates": [{"person_id":"p1","rank":1,"status":"possible|excluded|needs_review","score":3,"reasons":["explainable criterion"],"citations":[]}],
  "next_actions": [{"id":"a1","title":"...","reason":"...","person_ids":[],"document_ids":[]}],
  "audit": [{"id":"e1","timestamp":"...","action":"...","description":"..."}],
  "metrics": {"documents_processed":0,"supported_relationships":0,"conflicts":0,"remaining_candidates":0}
}

score is an explicitly labeled heuristic evidence score, not probability or scientific confidence. Candidate ranking must derive from available evidence/constraints; keep unknown-identity ground truth in evaluation fixtures only, outside runtime ranking inputs. Quote/line citations must locate real text. Simulated DNA matching may be represented in documents initially with explicit assumptions and no claims of sequence-level inference.

## Manifest semantics
Canonicalize the evidence/derived-assertion content with stable ordering. Exclude changing generation timestamps and external anchor metadata from the digest so repeated reads are stable. Tests must prove byte/content change detection and stable repeat reads. Do not call local verification blockchain verification. Chain anchoring endpoints may be added by agreement in milestone two.

## Additive offline handoff API

GET /api/cases/{case_id}/package returns export_schema_version=1, package_type=kinfold_research_package, generated_at, notice, a consistent snapshot, source_provenance table, and the standard manifest envelope. It is captured under the repository lock. Export timestamps and audit history are outside the evidence digest. Documents optionally include provenance: origin, original_name, received_at (null for fixture), text_sha256, authenticity. Captured text hashes are not silently rewritten when stored source text changes. Their role is change detection, not source authenticity.

The package verifier recomputes the manifest, compares its evidence fields with the snapshot, checks captured source fingerprints and locatable citation spans, and accepts an optional independently saved comparison digest. It does not establish evidence truth, identity or on-chain status. Models contribute validated annotations only; deterministic claims/constraints remain the record parser's output. Cyclic or malformed parent assertions are retained, flagged disputed and excluded from family-path scoring.
