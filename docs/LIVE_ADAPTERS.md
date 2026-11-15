# Runtime adapters and extraction boundaries

The core is a deterministic, locally stored synthetic demo. A subscription to a coding/chat product does not automatically configure API credentials for this application. No live-service success is claimed by the build.

## Supported local text patterns

Demo extraction recognizes these line-level forms (names and years are variable):

```text
Candidate lead: Miriam Stone.
Miriam Stone was born in 1972 in Newark, New Jersey.
Miriam Stone is the daughter of Thomas Mercer and Alice Mercer.
Thomas Mercer is a parent of Miriam Stone.
Thomas Mercer married Alice Mercer.
Thomas Mercer died in 2002.
Miriam Stone was recorded alive in 2009 in Newark, New Jersey.
Estimated birth year range: 1969-1977.
Estimated death year: 2011.
Case region: New Jersey.
DNA match: Unidentified individual and Ruth Mercer share 220 cM (simulated).
```

`son`, `daughter`, and `child` are accepted. Original source lines and contradictory assertions are retained. Unrecognized prose is marked reviewed without structured extraction, remains readable, and contributes no invented facts. Uploaded records are unverified user-supplied content even when their text says “synthetic.” There is no PDF/OCR/image/DNA-file ingestion in the core.

One deterministic investigation step reviews up to four pending records. Three steps is the server execution cap, even when a client requests five. Questions prioritize lexical record relevance; they do not change rules or run commands. All reviewed evidence is then used to rebuild relationships, conflicts, candidate criteria, and next actions.

Scores add +2 for birth-range fit, +1 for a pre-recovery life-status source, +1 for a source in the case region, and +2 for a record-derived family path to a simulated match. These are transparent heuristics, not probabilities. Exclusions depend on explicit case/source assumptions; conflicting case constraints abstain. A model annotation cannot change a candidate score.

## Install optional packages

```powershell
.venv/Scripts/python -m pip install -r requirements-optional.txt
Copy-Item .env.example .env
```

Edit `.env` locally, keep it out of Git, and restart `npm start`. No client-side `VITE_` variable should contain an API key. Install success and configuration flags are distinct from a successful live invocation. The case research log records actual adapter success/failure; missing credentials or a failed AI call preserve deterministic results and never claim live success.

## Gemini structured annotation

Set `KINFOLD_AI_MODE=gemini`, a server-side `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), and an explicit current `GEMINI_MODEL`. There is no guessed or hardcoded model ID. Select a model supported by your Google account and the [official model documentation](https://ai.google.dev/gemini-api/docs/models).

Pressing **Run investigation** invokes the actual Google GenAI SDK. The request contains reviewed records with line numbers and known person IDs, and asks for a Pydantic observation schema. Code rejects unknown people, missing/forged citation spans, unreviewed sources, and explicit identity/confidence claims. Accepted annotations are prefixed **Model suggestion** and **Unverified model annotation**; they are separate from deterministic relationships and ranking. Schema validity and a located quote do not prove semantic correctness, so human review remains required.

The live context limit is 60,000 source characters; the SDK request times out at 45 seconds with one attempt. This path was tested with an offline transport fixture, not a real key. Reference: [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output).

## deepagents research loop

Set `KINFOLD_AI_MODE=deepagents` with the same server-side key and explicit `GEMINI_MODEL`. The real `deepagents.create_deep_agent` harness uses a Google chat model and four bounded domain tools:

1. `plan_research`: records a short plan.
2. `retrieve_records`: accepts case document IDs only and returns exact numbered lines.
3. `extract_observations`: validates schema, known people, retrieved source IDs and cited spans.
4. `check_evidence`: compares annotations with the deterministic conflict/constraint results.

The run must complete those phases and a final report before success is recorded. Only validated annotations are persisted; free-form report prose never changes ranking. Audit entries record the executed tool trace. There are at most eight model calls, twelve accepted tool calls, a 75-second orchestration deadline and a 60-second per-request model timeout with up to 3 retries on 429/5xx errors. A final in-flight request may extend beyond the orchestration deadline.

The harness uses an ephemeral `StateBackend`, no host/sandbox filesystem, no memory files, no skills and no external retrieval tool. The installed harness requires a virtual `read_file` placeholder; the profile excludes it from the model, and execution middleware rejects it and every non-domain tool. Default delegation is disabled for the actual Google model; shell, task, write/edit/delete/glob/grep tools are absent. Prompt instructions alone are not the restriction.

Tests compile the real Google harness without a network call, execute the actual harness against a scripted offline model, complete the research phases, and verify a fabricated file-read call is denied. This verifies orchestration and restrictions, not a successful live Gemini run or sponsor eligibility. References: [deepagents API](https://reference.langchain.com/python/deepagents/graph/create_deep_agent), [customization](https://docs.langchain.com/oss/python/deepagents/customization).

## Lead investigator (deepagents, `backend/investigator.py`)

On Candidate leads, **Investigate with the agent** (`POST /api/cases/{id}/agent`, optional `person_id`, defaulting to the top open lead) runs a second `create_deep_agent` harness. It investigates one lead, using the same restricted profile as the loop above. Its seven tools are thin wrappers over deterministic code:

- `list_leads`, `search_records` (2–60 characters, at most 15 hits) and `read_record` (at most 30 numbered lines).
- `test_dna_hypothesis`: a reference-range check from `data/dna_reference.json` against the observed cM, plus the recorded-pedigree checks.
- `verify_claim`: `extraction.verify` on lines the agent has already read.
- `propose_next_action` (at most 3) and `write_report` (refuses identity claims and percentages).

The agent decides what to call; Kinfold computes every result. The run is stored beside the case, outside the manifest. It never changes lead statuses or scores.

**Bounds:** 40 model calls, 40 tool calls, a 100-second deadline (under the UI's 120-second request timeout), and a 60-second per-request model timeout with 3 retries. When 6 tool calls remain, tool results tell the live model to wrap up and write its report. The first live run made one tool call per turn and ran out of a 24-call budget before reporting.

**Recordings:**
- A successful live run records only the agent's tool calls (not the results) in `data/agent_runs/<key>.json`, keyed by prompt version, target and the processed records' text hashes. It never overwrites an existing recording.
- Without a live model, or after a live failure (the UI says so), the endpoint replays the recorded calls through the same tools. Every result is recomputed, so a tampered quote is rejected on replay.
- A stored run is marked stale once the records change.

Tests drive the real harness with a scripted offline model. They cover the denied `read_file`, a verified and a rejected claim, a refused uncited claim, DNA tests, the refused identity report, replay, tamper rejection, no-overwrite, the failure fallback, injected-instruction records and the stale flag. **Recorded live run:** `gemini-3.5-flash`, 2026-11-15 01:55 UTC, on Lena Hale, in `data/agent_runs/`. The agent made 33 tool calls:
- It read all 12 records.
- It tested 7 DNA hypotheses. First cousin once removed, half first cousin, second cousin and 2C1R fit 220 cM; first cousin, great-aunt/niece and half aunt/niece don't.
- It submitted 8 claims; 7 were verified. The rejected one used Lena's person ID in place of her name, and the agent resubmitted it correctly.
- It proposed 3 next steps.
- Its first report was refused for being too long (1,585 characters); it rewrote it.

With no key set, the demo replays this run, recomputing every result.

## MongoDB / Atlas persistence

Set `KINFOLD_STORAGE=mongodb`, `MONGODB_URI`, and optionally `MONGODB_DATABASE` (default `kinfold`). The real PyMongo adapter pings the configured server and stores case state in the `cases` collection. Configuration failure stops startup with a sanitized error; it does not silently choose local storage. Keep Atlas network access and credentials scoped appropriately for your development machine. Do not expose the URI in screenshots or frontend environment variables.

Verified against a real MongoDB Atlas cluster (free M0) on 2026-11-14. The full demo ran with `KINFOLD_STORAGE=mongodb`: reset, investigate, upload both Hale records, investigate again. A fresh app instance with a new client then reloaded the case with the same manifest digest and all AI findings. The offline database-contract tests still run without Atlas. Local JSON is the default and persists under `data/runtime/` unless `KINFOLD_DATA_DIR` is set. Both adapters target a single API worker; distributed/multi-process write coordination is not implemented. Case source text is capped at 5 MB across 100 records. Reference: [PyMongo connection documentation](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/).
