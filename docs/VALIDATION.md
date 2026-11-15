# Validation record

Observed November 14, 2026 (America/New_York); checks re-run November 15, 2026 on `main` (`063bc07`). The local product is runnable. Team workflow is described in AGENTS.md.

| Check | Observed result |
| --- | --- |
| `.venv/bin/python -m pytest backend/tests research/genetics/tests -q` | **101 passed** (61 backend, 40 research; re-run on `063bc07`). Covers extraction/citation integrity, evidence-driven exclusions, renaming/new-candidate tests, constraint abstention, conflicting parent chronology/cycles, upload/continuation, persistence, prompt injection, API bounds/errors, manifests, the DNA range check, AI extraction verification and replay, per-item annotation validation, anchoring (mocked subprocess, plus the real `anchor.mjs` preview), CRLF uploads, the deepagents investigator with a scripted model, and the hash-verified research artifacts. |
| `.venv/Scripts/python scripts/evaluate.py` | **PASS** on 2 separate synthetic families: 6 candidate decisions, 36 cited references. Expected outcomes live in evaluation fixtures only, outside runtime ranking inputs. This small correctness check is not scientific genetic validation. |
| `npm run test:integration -- --reset-demo` | **PASS** against the actual running HTTP API (82 citation references on the November 15 re-run), stable manifests, cross-language Python/JavaScript digest equality, upload, continued investigation, old-digest mismatch, and honest not_anchored status. This command resets the synthetic case. |
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

Updated November 14–15, 2026 (UTC) after real runs. Each entry names the PR or issue where the run is recorded.

- **Gemini extraction (uploads):** live `gemini-3.5-flash` runs on both Hale records. The real responses are committed in `data/ai_cache/` (#7) and replayed and re-verified offline. A failed live call falls back to the recording and says so. Re-run live on #17: obituary 11 proposed, 8 verified; birth announcement 4 proposed, 3 verified; Lena Hale `possible`.
- **Gemini annotations (Run investigation):** live on #17 after the per-item validation fix: `provider_success`, 10 validated annotations, 0 rejected. A later call in the same minute got a `ClientError`, most likely the free-tier rate limit; deterministic results were unaffected.
- **deepagents lead investigator:** one complete live `gemini-3.5-flash` run on Lena Hale (2026-11-15 01:55 UTC, #19), recorded in `data/agent_runs/`:
  - read all 12 records;
  - tested 7 DNA hypotheses (4 fit 220 cM);
  - 7 of 8 claims verified, and the rejected one was resubmitted correctly;
  - 3 next steps;
  - the first report was refused as too long and rewritten.

  An earlier live attempt ran out of its tool budget before reporting. Without a key, the demo replays the recorded calls and recomputes every result.
- **MongoDB Atlas:** a real free M0 cluster (#11). The full demo ran with `KINFOLD_STORAGE=mongodb`, and a fresh app instance reloaded the case with an identical manifest digest. JSON remains the default storage.
- **Solana devnet:** three real Memo transactions from the app's **Anchor this state** (#3), each checked via devnet RPC (finalized, memo equal to the manifest digest) and with in-app Verify:
  - Hale state with Lena Hale `possible`, the acceptance anchor: [4qWrFgPT…RpwFV](https://explorer.solana.com/tx/4qWrFgPTGC8wxif392icaBQM7ijpqc289k48GWndCpMFhM4q4k3yZ5MfAwEoVBrE9qeMuN3q9BCHbTj48jRWpwFV?cluster=devnet), digest `2b1d9685…f48a`;
  - two earlier states: [2HnRhAr9…poRAV](https://explorer.solana.com/tx/2HnRhAr9iAqJ8FqpVuD31CgVXizZQVQfYPbVJT6oYXUCMcRG5ymKG1D1zLVbJ1ZVw8WFxvFfgDTewxwB9NnpoRAV?cluster=devnet) and [5tPFJY6B…yXRwW](https://explorer.solana.com/tx/5tPFJY6Bg78JTAh8QWBfNuK6yxi27AUkTkt5QJ5xeZP4tM7x7d9RE1bMVXxPPrjoxfDqv86Ng8aEdNDr1R6yXRwW?cluster=devnet).

  The UI says "anchored" only for a confirmed anchor of the current digest; otherwise it says "not anchored". An anchor proves a state existed unchanged; it does not prove the records are true.

## Material limits

The deterministic parser recognizes documented line-level patterns, not arbitrary document semantics. Unsupported prose remains available and is labeled reviewed without structured extraction. No PDF/OCR or DNA sequence ingestion, calibrated genetic likelihood, identity confirmation, model training, public-profile scraping or real-person identification is implemented. Model annotations remain separate from deterministic ranking and require human review. Local single-worker persistence is not a deployed multi-user forensic system. The Arlequin team confirmed the project fits its AI-Driven Forensics track (#4).

Exact setup and parser rules: docs/LIVE_ADAPTERS.md. Optional devnet verification: blockchain/README.md. Genetic research stretch: docs/GENETIC_RESEARCH_NEXT.md.

## Final offline handoff checks

_Historical: recorded at the end of the original offline build, before the live runs above. Its "pending" and "not anchored" statements are superseded by the section "Optional adapters: implemented versus live-tested"._

- `npm run test:package`: **3 passed**. Source fingerprint tampering is caught even if an attacker recomputes the bundled manifest; snapshot divergence, forged citations and an incorrect comparison digest are rejected.
- Source fingerprints are captured on fixture load or upload, persist with the record, and appear in the source reader. Legacy records without one are reported explicitly. Package capture is atomic with the snapshot/manifest under the repository lock.
- Browser research-pack export succeeded at mobile390px with no alert/console error. Source provenance opened with the exact cited line2. Loaded-case document width390px equals viewport390px; the820px graph scrolls inside its288px viewport rather than expanding the page.
- Loaded-case desktop Lighthouse snapshot after final contrast fixes: accessibility100, best practices100, SEO100. The unrelated llms.txt/agentic-browsing audit remains50; no public crawler endpoint is needed for this local application.
- Held-out binary retention/exclusion comparison: birth-range-only baseline4/6, full record engine6/6 on the two manually authored families. The full status checks and36 citation references also pass. These tiny synthetic counts are not generalization, forensic accuracy or scientific confidence estimates.
- Sample upload records, a two-minute walkthrough and an accuracy-qualified Devpost draft are included. Real provider credentials, remote service calls, a development wallet/chain transaction and genetic inference remain outside completed offline scope.

Final sample verification: exported original10-record research package, verified10/10 captured source fingerprints and72 citation references with no external comparison digest. Standalone manifest validated by Solana CLI preview: status not_anchored. No network RPC/key read/sign/send in preview. UI restored to clean ten-record reviewed case. Deliverables are saved in the build chat outputs directory, including source archive, sample package, manifest, screenshot, demo script and Devpost draft. Offline scope complete; live API/database/wallet steps explicitly pending human setup.

The final interface was inspected with a native browser screenshot. File export through the browser tool to the build-chat output directory was unavailable, so no screenshot file is included in the handoff artifacts. The runnable app, source archive and research-package exports are unaffected.
