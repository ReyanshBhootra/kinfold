# Genetic research status

VERSION2 bounded fallback repair COMPLETE (2026-11-14). Finished by Claude Code after the Codex build chat stopped; Codex had already frozen the protocol and run the evaluation.

- Findings: `VERSION2_FINDINGS.md` (improvements, regressions and limits).
- Artifacts: `results/v2/` (frozen_protocol.json + sha256, frozen_split.csv.gz, comparison.json). v1 artifacts preserved byte-identical in `results/v1_preserved/` and hash-verified during evaluation. These artifacts are committed (see `.gitattributes`: no line-ending conversion, so the hashes hold on every OS).
- Tests: `.venv/Scripts/python -m pytest backend/tests research/genetics/tests -q` → 52 passed.
- Headline: unknown-provenance coverage restored from 0.746 to 0.906 (nominal 0.90). Wrong reliability assumptions remain unhandled (coverage 0.757). The evaluation is a data-reuse reanalysis, not fresh independent data.

The working Kinfold app is untouched. No new downloads, models, credentials, workers or AI calls.

VERSION3 source-reliability check COMPLETE (2026-11-14, branch `research/v3-reliability-check`).

- Findings: `VERSION3_FINDINGS.md`. Code: `version3.py`. Tests: `tests/test_version3.py`. Artifacts: `results/v3/` (frozen protocol + sha256, comparison.json).
- A label-free, batch-level z-test rejects sources that agree with the DNA evidence worse than assumed, then falls back to DNA only. Wrong-source coverage goes from 0.757 to 0.905 at batch size 100 or more, and the three new unseen wrong-source scenarios are also fixed at 400. Small batches (25) are still below nominal (0.865–0.880).
- All tests: 61 passed.

Next research step (not started): estimate a corrected reliability instead of discarding a rejected source, then test on fresh, independently seeded Ped-sim runs covering broader relationship types.
