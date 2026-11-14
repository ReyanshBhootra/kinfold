# Kinfold

**Every connection, a source.** An evidence-linked forensic genealogy research workspace for HackPrinceton Fall 2026.

Kinfold reads a disclosed synthetic case, reconstructs source-backed family relationships, preserves conflicting claims, narrows candidate leads through explainable constraints, and recommends the next record to check. It supports human review. It does not identify real people or turn simulated DNA matches into scientific confidence scores.

## Run locally

Use Python 3.11+ and Node 22.12+ (Node 24 is used for this build). No API key, database account, wallet, GPU, or model download is required for the core demo. Run commands from this repository.

Create a Python environment and install the backend dependencies:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
npm install
```

After installation, start both services with `npm start` and open **http://127.0.0.1:5173**. Ctrl+C stops both. The launcher refuses occupied ports to avoid duplicate servers.

For separate terminals, start the API:

```powershell
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
npm run dev
```

Open **http://127.0.0.1:5173**. Vite forwards `/api` and `/health` to the backend on port 8000. The frontend loads an existing case, or creates the synthetic demo if none exists. Reloading the browser does not deliberately reset the case. **Research log → Reset synthetic case** is the explicit reset action and discards uploaded records in that case.

On macOS/Linux use `.venv/bin/python` in place of `.venv/Scripts/python`. `frontend/.env.example` documents the optional `VITE_API_URL` override. Preview a production build with `npm run build` and `npm run preview`; the backend must still be running.

## Walk through the demo

1. Read the synthetic-data disclosure and case summary. The family graph is built from the actual API snapshot. Select a person, focus their branch, zoom, and inspect their cited relationships.
2. Select **Run investigation**. The local engine reviews actual fixture text and returns structured findings, candidate constraints, contradictions, and next research actions. No live AI result is fabricated.
3. Follow a citation chip. The source reader opens the actual document, displays line numbers, highlights the cited span, and shows the exact excerpt. Conflicting evidence stays visible in the findings.
4. Open **Candidate leads**. Review reasons for retaining or excluding each lead. The evidence score is heuristic, never an identity probability.
   The **DNA check** follows recorded parent links to the closest common ancestors with the DNA match. It then compares the shared cM with the reference range for that relationship. Ranges are 99% intervals from Ped-sim for first to third cousins, and approximate Shared cM Project ranges otherwise (`data/dna_reference.json`). In the demo all three recorded leads would be Ruth Mercer's nieces, and 220 cM is far too little for that, so the next action points to more distant branches. This is a consistency check, not a likelihood.
5. Upload `data/examples/synthetic-hale-obituary.txt` and `synthetic-hale-birth-announcement.txt`, then investigate. **AI extraction** asks Gemini for typed claims, each with a quote and line span. Kinfold keeps a claim only when the quote is verbatim in those lines and names every person and year it asserts. Rejected claims are listed with the reason. In the demo, the new records tie Frances Hale, Arthur Mercer's sister, to her granddaughter Lena Hale. Kinfold then proposes Lena as a lead whose birth year, region and DNA all fit. AI extraction needs a Gemini key, or a response recorded earlier in `data/ai_cache/`. Without either, uploads are kept for manual review and no AI result is invented.
6. Open **Evidence integrity**, export the manifest, and save a comparison digest. Add a synthetic/public text record with **Add evidence**, then run the investigation again. Comparing to the earlier digest detects changed content.
7. Review the **Research log** and export it. The integrity panel says **Not anchored on-chain** unless a confirmed Solana devnet transaction anchors the current digest (see below).

Text uploads support `.txt`, `.md`, and `.csv`, or pasted text. Preserve line breaks for useful citations. The UI caps files at 100 KB and text at 100,000 characters; the backend applies its own validation. Uploaded sources are untrusted evidence, not tool instructions. Keep private DNA, personal accounts, and sensitive real-person records out of this demo.

## Optional Solana devnet anchoring: the lead timeline

**Every lead gets a tamper-evident timeline.** **Evidence integrity → Anchor this state** records the current manifest digest on Solana devnet. The digest covers:
- the cited records;
- the AI's raw outputs (`ai_recordings`, the SHA-256 of each recorded Gemini reply);
- the lead decisions.

Only `kinfold:v1:sha256:<digest>` goes on-chain, in a Memo transaction: no names, DNA or records. Each anchor lists what changed since the previous one, links to Solana Explorer, and can be re-checked on-chain with **Verify**. If the evidence changes later, the panel says "current evidence differs from anchor #N". An anchor proves this exact state existed by that time, unchanged. **It does not prove the records are true.**

Setup takes about 5 minutes. Use a devnet-only wallet and never commit it:

```powershell
solana-keygen new --outfile C:/path/outside/repository/kinfold-dev.keypair.json
solana airdrop 1 --url devnet --keypair C:/path/outside/repository/kinfold-dev.keypair.json
```

Add `KINFOLD_SOLANA_KEYPAIR=C:/path/outside/repository/kinfold-dev.keypair.json` to `.env` and restart. The path must be absolute and outside the repository. Without it, anchoring returns setup help and nothing is sent. If the faucet rate-limits you, use https://faucet.solana.com.

The backend calls the same CLI (`blockchain/anchor.mjs`) used below. It stores an anchor only after the script confirms the transaction and checks its memo on-chain. Anchors are stored outside the manifest, so a digest never covers its own anchor. The CLI also works on its own:

```powershell
npm run anchor -- --manifest C:/path/to/exported-manifest.json
npm run anchor -- --help
```

See [blockchain/README.md](blockchain/README.md) for explicit send commands, receipt handling, and on-chain verification. A CLI receipt file is never imported or trusted by the UI.

## Checks

```powershell
npm run build
npm run test:anchor
.venv/Scripts/python -m pytest backend/tests -q
.venv/Scripts/python scripts/evaluate.py
# Requires a running LOCAL backend. This resets the synthetic demo and adds a test record.
npm run test:integration -- --reset-demo
```

The integration check calls the real HTTP API, locates every returned citation in source line spans, checks explainable exclusions and contradictions, recomputes the backend's exported digest in JavaScript, verifies stable reads, uploads a record, continues the investigation, and proves that an old digest no longer matches. See `docs/VALIDATION.md` for checks actually run and remaining limitations.

## Project boundaries

- `frontend/`: React, TypeScript, Vite. Investigation graph, source reader, candidate review, upload, research log, manifest export/verification. No frontend fixture impersonates the backend.
- `backend/`, `data/`: FastAPI evidence pipeline, synthetic records, deterministic constraints, repository/provider adapters, backend tests. See docs/LIVE_ADAPTERS.md for real optional Gemini/deepagents/MongoDB setup and actual supported modes.
- `blockchain/`: optional devnet Memo anchor and verifier, with offline tests.
- `docs/CONTRACT.md`: shared API and manifest semantics.
- `AGENTS.md` / `CLAUDE.md`: how the team and its AI agents coordinate through GitHub issues and PRs.

## Material limitations

This is a local research prototype, not a validated forensic system. Simulated cM summaries do not provide sequence-level genetic inference, calibrated relationship likelihoods, or a confirmed identity. Record-derived constraints and model prose must remain separate. Optional provider credentials and a real successful invocation are needed before claiming Gemini, MongoDB Atlas, or deepagents use. The offline demo is fully useful without them.

Public research datasets, pedigree simulation, relationship inference evaluation, and held-out-family baselines are stretch work. There is no model training or validated genetic benchmark in the core. Arlequin genetic genealogy eligibility still requires organizer confirmation. Sponsor integrations and prize eligibility must be described from implemented, verified behavior rather than intent.

Development binds to loopback. Do not expose this unauthenticated prototype publicly. No purchase, deployment, account scraping, private-profile research, or real-person identification is part of this build.


Optional runtime configuration and exact parser boundaries: [docs/LIVE_ADAPTERS.md](docs/LIVE_ADAPTERS.md). The real adapters are implemented and covered by offline tests; credentials and a successful real invocation are still needed before claiming live service use.


## Offline research handoff

Select **Export research pack** to download source records, source fingerprints, candidate reasoning, contradictions, next actions, audit history and manifest in one consistent JSON package. Verify it locally:

```powershell
npm run verify:package -- --file C:/path/to/kinfold-research-package.json
# Optional: compare with an independently saved earlier manifest digest.
npm run verify:package -- --file C:/path/to/kinfold-research-package.json --digest YOUR_SAVED_SHA256
npm run test:package
```

This checks local consistency and source changes; it cannot certify source truth, authorship or an identity. Export timestamps/audit history are outside the evidence digest. Records captured before provenance was added are explicitly reported without a captured fingerprint; reset the synthetic case for the current complete fixture.

Ready-to-upload examples live in data/examples/. The upload dialog explains accepted demo text patterns. See [two-minute demo](docs/DEMO_SCRIPT.md) and [Devpost draft](docs/DEVPOST_DRAFT.md). The draft clearly separates the no-key demo from live service use and sponsor eligibility.
