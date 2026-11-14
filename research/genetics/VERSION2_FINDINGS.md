# Version 2 findings: matching score/threshold fallback repair

**Scope:** a bounded prototype repair of one defect found in v1. It is not new genetics, not a validated forensic method, and not integrated into the Kinfold app.

## The defect (v1)

When record provenance was unknown, v1 switched to **DNA-only scores** but kept the **fused-record thresholds**. Scores and thresholds then came from different calibration families, so the claimed 90% set coverage no longer held. v1 measured 0.736 coverage with unknown lineage.

## The repair (v2)

- `Scores` and `Calibration` both carry a `family` tag, and `checked_set` raises an error if they don't match. A mismatch can no longer happen silently.
- **Routing policy:** grouped record fusion is used only when the bundle has origins A and B, both known and present, each internally consistent, and each at its assumed reliability. For every other bundle (no records, a missing origin, an unknown or unsupported origin, a conflicting copy, or an unexpected reliability), the method uses DNA scores **with DNA calibration**. Partial record information is discarded on purpose.
- v1 artifacts are preserved and hash-checked: `results/v1_preserved/`, plus the v1 hashes in `results/v2/frozen_protocol.json`.

## Protocol (frozen before evaluation)

- Protocol SHA-256: `2f70cc2af9c490a104e6d957f2f54a94a2dab0e737c78eadcc10ff97a7648f6e`. The protocol, split, data manifest, DNA model and implementation hashes are re-checked before evaluation runs.
- **Split:** v1 *calibration* groups are divided by a fixed salted hash into v2-calibration and v2-evaluation. v2-calibration uses batch 1 only and v2-evaluation uses batch 2 only. Matching (cousin, replicate) IDs always stay together. The whole v1 test partition is excluded. Positive-sharing groups: 20,772 calibration and 21,004 evaluation, with zero overlap (checked at runtime and by tests).
- The DNA model is reused unchanged: the v1 cM+segment histogram, trained only on v1 train groups. All thresholds were recalibrated on v2-calibration rows. Nominal coverage is 0.90.
- **Data reuse caveat:** these are **not fresh, independent data**. The batch-2 evaluation rows were never scored before, but their group IDs had batch-1 counterparts in v1 calibration. No wholly unused source groups remain. Seed independence of the published simulations cannot be certified. Treat this as a reanalysis, not a generalization test.
- Records are fabricated with a new frozen seed. Assumed reliabilities are invented: A = 0.85, B = 0.70.

## Results (21,004 evaluation pairs; full1C–8C, positive sharing, ss_intf)

| Scenario | Method | Coverage | Mean set size | Abstain | Empty set |
|---|---|---|---|---|---|
| clean complete | v1 logic | 0.948 | 1.05 | 0.076 | 0.015 |
| | **corrected** | 0.901 | 0.96 | 0.065 | 0.054 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |
| nominal missing 25% | v1 logic | 0.907 | 1.10 | 0.113 | 0.026 |
| | **corrected** | 0.904 | 1.43 | 0.237 | 0.031 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |
| missing 70% | v1 logic | **0.816** | 1.36 | 0.266 | 0.050 |
| | **corrected** | **0.906** | 1.93 | 0.423 | 0.008 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |
| incorrect A reliability (45% error) | v1 logic | 0.861 | 1.08 | 0.146 | 0.036 |
| | **corrected** | **0.757** | 0.89 | 0.138 | 0.124 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |
| all origins unknown | v1 logic | **0.746** | 1.66 | 0.431 | 0.071 |
| | **corrected** | **0.906** | 2.02 | 0.458 | 0.004 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |
| A origin unknown | v1 logic | 0.828 | 1.12 | 0.166 | 0.048 |
| | **corrected** | **0.906** | 2.02 | 0.458 | 0.004 |
| | DNA only | 0.906 | 2.02 | 0.458 | 0.004 |

Per-class breakdowns, routing counts and thresholds are in `results/v2/comparison.json`.

## What improved

- **Unknown provenance:** coverage went from 0.746 to 0.906 (all origins unknown) and from 0.828 to 0.906 (A unknown), back at the nominal 0.90. That is the defect being repaired.
- **Heavy missingness (70%):** coverage went from 0.816 to 0.906.
- **Fallback correctness:** every fallback row produced exactly the same set as the DNA-only baseline (0 disagreements in all scenarios), so the fallback is now a true DNA-only fallback.
- **Complete, correct records:** the corrected method stays near nominal (0.901) and reduces the mean set size from 2.02 (DNA only) to 0.96.

## What did not improve or got worse

- **Wrong reliability assumptions are not handled.** When A's records are wrong 45% of the time but labeled 85% reliable, the bundle passes the completeness check, so it is fused. Coverage falls to 0.757, which is *worse* than v1 logic (0.861) and far below DNA only (0.906). The repair targets provenance metadata, not mis-specified reliability. Detecting that would need a reliability estimator, which is out of scope.
- **Empty sets rose with complete fusion** (5.4% clean, 12.4% with wrong reliability). Mean set size below 1 means the method sometimes rules out every hypothesis. Treat an empty set as "conflicting evidence, review manually", never as a conclusion.
- **Discarding partial records costs efficiency.** In the 25%-missing case, coverage holds, but sets are larger (1.43 vs 1.10) and abstention is higher (0.237 vs 0.113) than v1 logic.
- **v1 logic beats nominal in the clean case (0.948)** only because its thresholds were calibrated on the 25%-missing mixture, which makes it conservative for clean data. That is luck, not a property of v1.
- **Distant cousins remain thin:** only 47 calibration rows for 8C and 146 for 7C (positive sharing).

## What remains unproven

- Generalization to fresh, independently seeded simulations, other crossover models or other relationship types (half, avuncular, unrelated, endogamy).
- Any real-record behavior. Records here are fabricated direct cousin-degree claims with invented reliabilities.
- Novelty. Error-tolerant pedigree reconstruction (for example Bioinformatics 2026 btag251, repare, Bonsai) and conformal methods are existing related work.

## Reproduce

```bash
.venv/Scripts/python -m research.genetics.version2 freeze     # refuses if already frozen
.venv/Scripts/python -m research.genetics.version2 evaluate   # refuses if comparison.json exists or any frozen hash changed
.venv/Scripts/python -m pytest backend/tests research/genetics/tests -q
```

To re-run from scratch, move `results/v2/` aside first. The scripts never overwrite saved v2 artifacts.

Verification on 2026-11-14: 52 tests passed (backend + research, including the v2 regression tests for family mismatch, fallback routing and split leakage). Evaluation runtime was about 8 s on CPU. No AI calls, paid compute or real-person data were used.
