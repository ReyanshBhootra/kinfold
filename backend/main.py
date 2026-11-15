from uuid import uuid4
from datetime import datetime, timezone
import hashlib
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from .engine import derive
from .manifest import evidence_manifest
from .models import InvestigationRequest, UploadRequest, VerifyRequest
from .repository import configured_repository, current_actor, event
from .providers import ProviderError, configured_provider
from .extraction import configured_extractor, extract_document
from . import anchors as anchoring
from . import investigator
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()
_UNSET = object()


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: str | None = Field(default=None, max_length=80)


def create_app(repository=None, provider=None, extractor=_UNSET, agent=_UNSET):
    app = FastAPI(title="Kinfold evidence research API", version="0.1.0")
    app.state.repository = repository or configured_repository()
    app.state.provider = provider if provider is not None else configured_provider()
    app.state.extractor = configured_extractor() if extractor is _UNSET else extractor
    app.state.agent = investigator.configured_chat() if agent is _UNSET else (agent or (None, None))
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Kinfold-Researcher"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        messages = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

    @app.exception_handler(anchoring.AnchorError)
    async def anchor_error(_request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    @app.middleware("http")
    async def researcher_name(request: Request, call_next):
        # Self-declared display name for the case activity log; printable characters only, bounded.
        raw = request.headers.get("x-kinfold-researcher", "")
        name = "".join(ch for ch in raw if ch.isprintable()).strip()[:60] or None
        token = current_actor.set(name)
        try:
            return await call_next(request)
        finally:
            current_actor.reset(token)

    @app.middleware("http")
    async def bounded_body(request: Request, call_next):
        # Includes UTF-8/JSON escaping overhead above the 100,000-character model bound.
        if request.method == "POST":
            body = await request.body()
            if len(body) > 800000:
                return JSONResponse(status_code=413, content={"detail": "Request body exceeds the local 800 KB limit."})
        return await call_next(request)

    def get(case_id):
        try:
            return app.state.repository.get(case_id)
        except KeyError:
            raise HTTPException(404, "Case not found") from None

    def snap(state):
        """Derived snapshot plus the lead timeline. Anchors sit outside the evidence manifest."""
        current = derive(state)
        digest = evidence_manifest(current)["digest"]
        current["anchors"] = [anchoring.public(a, digest) for a in state.get("anchors", [])]
        run = state.get("agent_run")
        # The latest agent run, also outside the manifest. Marked stale once the records it read have changed.
        current["agent_run"] = {**run, "stale": run["records_key"] != investigator.recording_key(current, run["target"]["person_id"])} if run else None
        return current

    def manifest_for(state):
        current = derive(state)
        envelope = evidence_manifest(current)
        match = next((a for a in reversed(state.get("anchors", [])) if a["digest"] == envelope["digest"]), None)
        if match:  # stored only after anchor.mjs confirmed the transaction and checked its memo on-chain
            envelope["anchor"] = {"status": "anchored", "network": "solana-devnet", "transaction": match["transaction"],
                                  "explorer": match["explorer"], "anchored_at": match["anchored_at"], "number": match["number"]}
        return current, envelope

    @app.get("/health")
    def health():
        selected = app.state.provider
        active = bool(selected and selected.configured)
        return {"status": "ok", "mode": "live" if active else "demo", "ai_extraction": "live" if app.state.extractor else "replay_only",
                "providers": {"gemini": active and selected.name == "gemini", "mongodb": app.state.repository.kind == "mongodb", "deepagents": active and selected.name == "deepagents"},
                "storage": app.state.repository.kind, "setup_issue": getattr(selected, "reason", None), "provider_status_means": "Configured adapter; successful runs are recorded in the case audit."}

    @app.get("/api/cases")
    def cases():
        return {"cases": [{k: case[k] for k in ("id", "title", "status", "synthetic")} for case in app.state.repository.list()]}

    @app.post("/api/cases/demo")
    def reset_demo():
        """Explicit reset: replaces the demo, including uploads, with the original fixture."""
        return snap(app.state.repository.reset_demo())

    @app.get("/api/cases/{case_id}")
    def snapshot(case_id: str):
        return snap(get(case_id))

    @app.post("/api/cases/{case_id}/documents")
    def upload(case_id: str, body: UploadRequest):
        with app.state.repository.lock:
            state = get(case_id)
            if len(state["documents"]) >= 100:
                raise HTTPException(409, "The local prototype supports at most 100 records per case.")
            if sum(len(d["text"].encode("utf8")) for d in state["documents"]) + len(body.text.encode("utf8")) > 5_000_000:
                raise HTTPException(409, "The local prototype supports at most 5 MB of source text per case.")
            document = {"id": "upload-" + uuid4().hex[:12], "name": body.name.strip(), "text": body.text, "kind": "uploaded_text", "synthetic": False, "processed": False}
            document["provenance"] = {"origin": "user_upload", "original_name": document["name"], "received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                      "text_sha256": hashlib.sha256(body.text.encode("utf8")).hexdigest(), "authenticity": "Unverified user-supplied text; origin and claims require human review"}
            state["documents"].append(document)
            state["case"]["version"] += 1
            state["case"]["status"] = "evidence_added"
            state["audit"].append(event("document_added", f"Added unverified user-supplied text record: {document['name']}. Claims await review."))
            app.state.repository.put(state)
            return snap(state)

    @app.post("/api/cases/{case_id}/investigate")
    def investigate(case_id: str, body: InvestigationRequest):
        with app.state.repository.lock:
            state = get(case_id)
            pending = [d for d in state["documents"] if not d["processed"]]
            # One bounded deterministic step reviews up to four records; maximum three steps.
            tokens = {w.casefold() for w in body.question.split() if len(w) > 3}
            pending.sort(key=lambda d: (-sum(w in (d["name"] + " " + d["text"]).casefold() for w in tokens), d["id"]))
            reviewed = pending[:min(body.max_steps, 3) * 4]
            known_names = [p["name"] for p in derive(state)["people"]]
            for document in reviewed:
                document["processed"] = True
                # Uploaded records go through AI extraction (live, or a recorded replay); fixtures use the template parser.
                if document.get("kind") == "uploaded_text":
                    result = extract_document(document, known_names, app.state.extractor)
                    if result is not None:
                        state.setdefault("ai_extractions", {})[document["id"]] = result
                        if result["source"] == "failed":
                            state["audit"].append(event("ai_extraction_failed", f"{document['name']}: {result['note']}"))
                        else:
                            state["audit"].append(event("ai_extraction", f"{document['name']}: Gemini ({result['model']}, {result['source']}) proposed {result['proposed']} claim(s); {len(result['accepted'])} passed source verification, {len(result['rejected'])} rejected."))
            if reviewed:
                state["case"]["version"] += 1
            state["case"]["status"] = "reviewed" if all(d["processed"] for d in state["documents"]) else "reviewing"
            state["audit"].append(event("investigation_demo", f"Deterministic pass: reviewed {len(reviewed)} record(s), validated source spans, rebuilt relationships, retained conflicts and applied provisional constraints. Optional provider execution is recorded separately."))
            result = derive(state)
            selected = app.state.provider
            before_model = (state["case"]["mode"], state.get("model_findings", []))
            state["case"]["mode"] = "demo"
            if selected:
                try:
                    observations, trace = selected.extract(result, body.question)
                    state["model_findings"] = observations
                    state["case"]["mode"] = "live"
                    state["audit"].append(event("provider_success", f"Live {selected.name} adapter completed. " + " ".join(trace)))
                except Exception as exc:
                    # Never leak raw SDK exceptions: they can include request/auth details.
                    # ProviderError messages are Kinfold's own (error locations/types, never reply text or keys).
                    explanation = getattr(selected, "reason", None) or (str(exc) if isinstance(exc, ProviderError) else type(exc).__name__)
                    state["audit"].append(event("provider_unavailable", f"Live {selected.name} adapter did not complete ({explanation}). Deterministic results retained; no live success claimed."))
            if before_model != (state["case"]["mode"], state.get("model_findings", [])):
                state["case"]["version"] += 1
            app.state.repository.put(state)
            return snap(state)

    @app.get("/api/cases/{case_id}/manifest")
    def manifest(case_id: str):
        return manifest_for(get(case_id))[1]

    @app.get("/api/cases/{case_id}/package")
    def research_package(case_id: str):
        with app.state.repository.lock:
            state = get(case_id)
            current, envelope = snap(state), manifest_for(state)[1]
            provenance = []
            for document in current["documents"]:
                captured = document.get("provenance", {}).get("text_sha256")
                actual = hashlib.sha256(document["text"].encode("utf8")).hexdigest()
                provenance.append({"document_id": document["id"], "origin": document.get("provenance", {}).get("origin", "legacy_not_captured"),
                                   "captured_text_sha256": captured, "current_text_sha256": actual, "captured_hash_matches": captured == actual if captured else None})
            return {"export_schema_version": 1, "package_type": "kinfold_research_package", "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "notice": "Synthetic case and unverified leads. Heuristic scores are not probabilities. Hashes show consistency against a baseline, not evidence truth or identity. This file alone establishes no on-chain status; verify any listed anchor transaction on Solana devnet.",
                    "snapshot": current, "source_provenance": provenance, "manifest": envelope}

    @app.post("/api/cases/{case_id}/verify")
    def verify(case_id: str, body: VerifyRequest):
        actual = evidence_manifest(derive(get(case_id)))["digest"]
        return {"matches": body.digest.lower() == actual, "expected_digest": body.digest.lower(), "actual_digest": actual}

    @app.post("/api/cases/{case_id}/agent")
    def agent_run(case_id: str, body: AgentRequest):
        """Let the lead-investigator agent check one lead. Its report is stored outside the evidence manifest."""
        with app.state.repository.lock:
            current = derive(get(case_id))
        open_leads = sorted((c for c in current["candidates"] if c["status"] != "excluded"), key=lambda c: c["rank"])
        target = body.person_id or (open_leads[0]["person_id"] if open_leads else None)
        if target is None or target not in {c["person_id"] for c in current["candidates"]}:
            raise HTTPException(409, "No open candidate lead to investigate. Run the investigation first.")
        chat, model_name = app.state.agent
        try:  # the model calls run outside the repository lock
            run = investigator.investigate_lead(current, target, chat, model_name)
        except ProviderError as error:
            raise HTTPException(409, str(error)) from None
        with app.state.repository.lock:
            state = get(case_id)
            run["records_key"], run["case_version"] = investigator.recording_key(current, target), state["case"]["version"]
            state["agent_run"] = run
            label = "live" if run["source"] == "live" else f"replay of a recorded {run['model']} run from {run['recorded_at']}"
            state["audit"].append(event("agent_run", f"Lead investigator ({label}) checked {run['target']['name']}: {len(run['steps'])} tool calls, "
                                                     f"{len(run['dna_tests'])} DNA hypotheses tested, {len(run['verified_claims'])} claims verified, "
                                                     f"{len(run['rejected_claims'])} rejected. Lead statuses unchanged." + (f" {run['note']}" if run["note"] else "")))
            app.state.repository.put(state)
            return snap(state)

    @app.post("/api/cases/{case_id}/anchor")
    def anchor(case_id: str):
        anchoring.keypair_path()  # fail fast with setup help before any work
        with app.state.repository.lock:
            state = get(case_id)
            current, envelope = manifest_for(state)
        # The network call runs outside the lock; the state is re-checked before the anchor is stored.
        receipt = anchoring.send(envelope)
        with app.state.repository.lock:
            state = get(case_id)
            current, now = manifest_for(state)
            if now["digest"] != envelope["digest"]:
                raise HTTPException(409, f"The case changed while anchoring. Transaction {receipt['transaction']} anchors the earlier state; it was not recorded here.")
            previous = state.get("anchors", [])[-1] if state.get("anchors") else None
            entry = anchoring.record(envelope, receipt, current, previous)
            state.setdefault("anchors", []).append(entry)
            state["audit"].append(event("anchored", f"Anchor #{entry['number']}: manifest v{entry['version']} digest {entry['digest'][:12]}… recorded on Solana devnet in transaction {entry['transaction']}. {anchoring.LIMIT_NOTE}"))
            app.state.repository.put(state)
            return snap(state)

    @app.post("/api/cases/{case_id}/anchors/{number}/verify")
    def verify_anchor(case_id: str, number: int):
        state = get(case_id)
        stored = next((a for a in state.get("anchors", []) if a["number"] == number), None)
        if stored is None:
            raise HTTPException(404, "Anchor not found")
        on_chain, detail = anchoring.verify(stored)
        current = evidence_manifest(derive(state))["digest"]
        result = {"number": number, "verified_on_chain": on_chain, "detail": detail, "anchored_digest": stored["digest"], "current_digest": current,
                  "current_matches_anchor": current == stored["digest"], "transaction": stored["transaction"], "explorer": stored["explorer"], "limits": anchoring.LIMIT_NOTE}
        with app.state.repository.lock:
            fresh = get(case_id)
            outcome = "verified on devnet" if on_chain else f"NOT verified ({detail})"
            match = "current evidence matches it" if result["current_matches_anchor"] else "current evidence differs from it"
            fresh["audit"].append(event("anchor_verified" if on_chain else "anchor_verify_failed", f"Anchor #{number} {outcome}; {match}."))
            app.state.repository.put(fresh)
        return result

    return app


app = create_app()
