# Validation record

Observed November 14, 2026 (America/New_York). The local product is runnable. Team workflow is described in AGENTS.md.

| Check | Observed result |
| --- | --- |
| `.venv/Scripts/python -m pytest backend/tests -q` | **21 passed**. Extraction/citation integrity, evidence-driven exclusions, renaming/new-candidate tests, constraint abstention, conflicting parent chronology/cycles, upload/continuation, persistence, prompt injection, API bounds/errors, manifests and optional adapter checks. |
| `.venv/Scripts/python scripts/evaluate.py` | **PASS** on 2 separate synthetic families: 6 candidate decisions, 36 cited references. Expected outcomes live in evaluation fixtures only, outside runtime ranking inputs. This small correctness check is not scientific genetic validation. |
| `npm run test:integration -- --reset-demo` | **PASS** against the actual running HTTP API: 72 citation references, stable manifests, cross-language Python/JavaScript digest equality, upload, continued investigation, old-digest mismatch, and honest not_anchored status. This command resets the synthetic case. |
| `npm run build` | **PASS**, strict TypeScript plus production Vite bundle. |
| `npm run test:anchor` | **4 passed**: canonicalization/Unicode, tampering, exact Memo-program payload/signer verification, real SDK offline signing/serialization of a Memo-only transaction. |
| `.venv/Scripts/python -m pip check` | **PASS**, no broken requirements. |
| `npm audit` | **0 known vulnerabilities** at the SDK upgrade check; package lock retained. |
| `npm start` | **PASS**, starts API8000 and frontend5173. Confirmed companion service shuts down when one service exits; restarted successfully. |
| Browser against real API | Loaded case, selected graph person and inspected actual relationships, opened cited birth record and observed exact line2 highlighting, reviewed candidate reasons/exclusions, saved/verified unchanged digest, uploaded synthetic alive2014 record, re-investigated and observed remaining leads become0, then verified old digest mismatch. |
| Browser error state | Connection failure/retry and disabled case-dependent controls verified before backend startup. |
| Browser dialog/navigation | Source/about/manifest/upload dialogs opened; Escape closes; source quote and line span match actual document. Textarea typing/upload was exercised with real input events after the browser fill helper did not trigger React change state. |

The installed upstream LangSmith/deepagents stack emits 13 Python3.14 deprecation warnings about asyncio.iscoroutinefunction in the test run. They do not fail the tests; no local warning suppression was added.

## Optional adapters: implemented versus live-tested

- **Gemini:** real Google SDK client initializes without a call; offline transport verifies structured schema and citation validation. No real API key/request was used. Set KINFOLD_AI_MODE=gemini, GEMINI_API_KEY or GOOGLE_API_KEY, and explicit GEMINI_MODEL in server .env, then restart.
- **deepagents:** actual installed harness compiles for the Google model without a network request; actual harness executes plan/retrieve/extract/check phases using a scripted offline model, with an unauthorized file read denied. Live remote-model execution remains unverified.
- **MongoDB:** genuine PyMongo repository adapter implemented and offline database-contract behavior tested. No Atlas instance/connection was verified. JSON is active storage.
- **Solana:** optional devnet CLI implemented and offline tests pass. No wallet was read/funded, no transaction sent, and no on-chain anchor claimed. UI remains not_anchored; receipts alone are never trusted.

## Material limits

The deterministic parser recognizes documented line-level patterns, not arbitrary document semantics. Unsupported prose remains available and is labeled reviewed without structured extraction. No PDF/OCR or DNA sequence ingestion, calibrated genetic likelihood, identity confirmation, model training, public-profile scraping or real-person identification is implemented. Model annotations remain separate from deterministic ranking and require human review. Local single-worker persistence is not a deployed multi-user forensic system. Arlequin genetic genealogy eligibility remains unconfirmed.

Exact setup and parser rules: docs/LIVE_ADAPTERS.md. Optional devnet verification: blockchain/README.md. Genetic research stretch: docs/GENETIC_RESEARCH_NEXT.md.

## Final offline handoff checks

- `npm run test:package`: **3 passed**. Source fingerprint tampering is caught even if an attacker recomputes the bundled manifest; snapshot divergence, forged citations and an incorrect comparison digest are rejected.
- Source fingerprints are captured on fixture load or upload, persist with the record, and appear in the source reader. Legacy records without one are reported explicitly. Package capture is atomic with the snapshot/manifest under the repository lock.
- Browser research-pack export succeeded at mobile390px with no alert/console error. Source provenance opened with the exact cited line2. Loaded-case document width390px equals viewport390px; the820px graph scrolls inside its288px viewport rather than expanding the page.
- Loaded-case desktop Lighthouse snapshot after final contrast fixes: accessibility100, best practices100, SEO100. The unrelated llms.txt/agentic-browsing audit remains50; no public crawler endpoint is needed for this local application.
- Held-out binary retention/exclusion comparison: birth-range-only baseline4/6, full record engine6/6 on the two manually authored families. The full status checks and36 citation references also pass. These tiny synthetic counts are not generalization, forensic accuracy or scientific confidence estimates.
- Sample upload records, a two-minute walkthrough and an accuracy-qualified Devpost draft are included. Real provider credentials, remote service calls, a development wallet/chain transaction and genetic inference remain outside completed offline scope.

Final sample verification: exported original10-record research package, verified10/10 captured source fingerprints and72 citation references with no external comparison digest. Standalone manifest validated by Solana CLI preview: status not_anchored. No network RPC/key read/sign/send in preview. UI restored to clean ten-record reviewed case. Deliverables are saved in the build chat outputs directory, including source archive, sample package, manifest, screenshot, demo script and Devpost draft. Offline scope complete; live API/database/wallet steps explicitly pending human setup.

The final interface was inspected with a native browser screenshot. File export through the browser tool to the build-chat output directory was unavailable, so no screenshot file is included in the handoff artifacts. The runnable app, source archive and research-package exports are unaffected.
