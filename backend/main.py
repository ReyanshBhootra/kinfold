from uuid import uuid4
from datetime import datetime, timezone
import hashlib
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from .engine import derive
from .manifest import evidence_manifest
from .models import InvestigationRequest, PhotoConfirm, PhotoUpload, UploadRequest, VerifyRequest
from . import photos as paper
from .repository import configured_repository, event
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


def create_app(repository=None, provider=None, extractor=_UNSET, agent=_UNSET, transcriber=_UNSET):
    app = FastAPI(title="Kinfold evidence research API", version="0.1.0")
    app.state.repository = repository or configured_repository()
    app.state.provider = provider if provider is not None else configured_provider()
    app.state.extractor = configured_extractor() if extractor is _UNSET else extractor
    app.state.transcriber = paper.configured_transcriber() if transcriber is _UNSET else transcriber
    app.state.agent = investigator.configured_chat() if agent is _UNSET else (agent or (None, None))
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        messages = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

    @app.exception_handler(anchoring.AnchorError)
    async def anchor_error(_request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    @app.middleware("http")
    async def bounded_body(request: Request, call_next):
        # Includes UTF-8/JSON escaping overhead above the 100,000-character model bound.
        if request.method == "POST":
            body = await request.body()
            # Photo uploads carry a base64 image (at most 4 MB of bytes); every other request stays under 800 KB.
            limit, label = (6_000_000, "6 MB") if request.url.path.endswith("/photos") else (800000, "800 KB")
            if len(body) > limit:
                return JSONResponse(status_code=413, content={"detail": f"Request body exceeds the local {label} limit."})
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
        # Photographed records awaiting or past review. A confirmed photo's hash and line boxes enter the manifest
        # through its record's provenance; unconfirmed photos are not evidence yet.
        current["photos"] = state.get("photos", [])
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

    def find_photo(state, photo_id):
        photo = next((p for p in state.get("photos", []) if p["id"] == photo_id), None)
        if photo is None:
            raise HTTPException(404, "Photo not found")
        return photo

    @app.post("/api/cases/{case_id}/photos")
    def add_photo(case_id: str, body: PhotoUpload):
        """Paper to proof, step 1: hash the original bytes on arrival and store them unchanged."""
        try:
            data, sha256 = paper.decode_image(body.media_type, body.image_base64)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        with app.state.repository.lock:
            state = get(case_id)
            photos = state.setdefault("photos", [])
            if not any(p["sha256"] == sha256 for p in photos):
                if len(photos) >= 20:
                    raise HTTPException(409, "The local prototype supports at most 20 photos per case.")
                app.state.repository.put_blob(sha256, data)
                name = body.name.strip() or "Photographed record"
                photos.append({"id": "photo-" + uuid4().hex[:12], "name": name, "sha256": sha256, "media_type": body.media_type, "bytes": len(data),
                               "capture": body.capture, "received_at": paper.now(), "status": "captured", "transcription": None, "document_id": None})
                state["audit"].append(event("photo_added", f"Received photo \"{name}\" ({body.capture}, {len(data):,} bytes). SHA-256 {sha256[:16]}… recorded on arrival; the original bytes are stored unchanged."))
                app.state.repository.put(state)
            return snap(state)

    @app.get("/api/cases/{case_id}/photos/{photo_id}/image")
    def photo_image(case_id: str, photo_id: str):
        photo = find_photo(get(case_id), photo_id)
        try:
            data = app.state.repository.get_blob(photo["sha256"])
        except KeyError:
            raise HTTPException(404, "The original image is not in this storage backend.") from None
        if hashlib.sha256(data).hexdigest() != photo["sha256"]:
            raise HTTPException(409, "The stored image no longer matches the hash recorded on arrival.")
        return Response(content=data, media_type=photo["media_type"], headers={"Cache-Control": "no-store", "X-Content-SHA256": photo["sha256"]})

    @app.post("/api/cases/{case_id}/photos/{photo_id}/transcribe")
    def transcribe_photo(case_id: str, photo_id: str):
        """Paper to proof, step 2: Gemini reads the photo line by line, with a box per line. A proposal, not evidence."""
        with app.state.repository.lock:
            state = get(case_id)
            photo = find_photo(state, photo_id)
            if photo["status"] == "confirmed":
                raise HTTPException(409, "This photo's transcription is already confirmed as a record.")
            try:
                data = app.state.repository.get_blob(photo["sha256"])
            except KeyError:
                raise HTTPException(409, "The original image is not in this storage backend.") from None
            if hashlib.sha256(data).hexdigest() != photo["sha256"]:
                raise HTTPException(409, "The stored image no longer matches the hash recorded on arrival.")
            try:
                photo["transcription"] = paper.transcribe(photo, data, app.state.transcriber)
            except LookupError as exc:
                state["audit"].append(event("photo_transcription_failed", f"{photo['name']}: {exc}"))
                app.state.repository.put(state)
                raise HTTPException(409, str(exc)) from None
            t = photo["transcription"]
            photo["status"] = "transcribed"
            uncertain = sum(line["uncertain"] for line in t["lines"])
            state["audit"].append(event("photo_transcribed", f"{photo['name']}: Gemini ({t['model']}, {t['source']}) transcribed {len(t['lines'])} line(s), {uncertain} marked uncertain. Awaiting human confirmation against the photo." + (f" {t['note']}" if t["note"] else "")))
            app.state.repository.put(state)
            return snap(state)

    @app.post("/api/cases/{case_id}/photos/{photo_id}/confirm")
    def confirm_photo(case_id: str, photo_id: str, body: PhotoConfirm):
        """Paper to proof, step 3: a person confirms each line against the photo; the result becomes a record."""
        with app.state.repository.lock:
            state = get(case_id)
            photo = find_photo(state, photo_id)
            if photo["status"] != "transcribed":
                raise HTTPException(409, "Transcribe the photo first." if photo["status"] == "captured" else "This photo is already confirmed.")
            if len(state["documents"]) >= 100:
                raise HTTPException(409, "The local prototype supports at most 100 records per case.")
            try:
                document = paper.confirmed_document(photo, body.lines)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            document = {"id": "photo-doc-" + uuid4().hex[:12], **document}
            state["documents"].append(document)
            photo["status"], photo["document_id"] = "confirmed", document["id"]
            state["case"]["version"] += 1
            state["case"]["status"] = "evidence_added"
            corrections = len(document["provenance"]["corrections"])
            state["audit"].append(event("photo_confirmed", f"{photo['name']}: transcription confirmed by a person with {corrections} correction(s). Added as a record tied to photo SHA-256 {photo['sha256'][:16]}…; claims await review."))
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
                if document.get("kind") in ("uploaded_text", "photo_transcription"):
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
