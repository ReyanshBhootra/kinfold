# Version 3 findings: checking source reliability before fusion

**Scope:** a bounded prototype fix for the failure v2 left open. It is not new genetics, not validated forensic calibration, and not integrated into the Kinfold app.

## The problem (v2)

v2 fused any complete, known A/B record bundle at the source's *assumed* reliability. When source A was really wrong 45% of the time but labeled 85% reliable, coverage fell to **0.757** at a nominal 0.90. That was worse than ignoring records altogether (DNA only: 0.906).

## The fix (v3)

You can't tell whether a source is reliable from one record, so v3 checks each **source across a batch of cases** that cite it, **without using true answers**:

1. In each case, compute a residual: the DNA score of the degree the source claims, minus the score expected if the source had its assumed reliability.
2. Build a reference residual distribution from v2-calibration rows, where the fabricated records really have the assumed reliability (A: 15,530 residuals, B: 15,570).
3. Run a one-sided z-test per source (alpha 0.005 each, z < −2.576). The test only rejects sources that agree with the DNA evidence *worse* than assumed. Sources better than assumed are kept.
4. If a source is rejected, or cited by fewer than 10 cases in the batch, record fusion is turned off for that batch. Affected cases use DNA scores with DNA calibration, the v2 fallback. Otherwise, v2 routing is unchanged.

Integrity checks:
- v3 reuses the frozen v2 split and records (identical random draws).
- It recomputes v2's thresholds and refuses to run if they differ.
- It hash-checks the v2 code and results. v1 and v2 artifacts are untouched.

## Protocol and disclosures

- Frozen protocol SHA-256: `e09223c00d99ce0c72acf9e6322bab6aa831bf92fb080c66b3a0f68663d7d2f6` (`results/v3/frozen_protocol.json`). Evaluation was run once after freezing, with no tuning.
- **Designed after seeing the v2 failure on these same rows.** To counter that, four **new scenarios** were fixed in the protocol before any v3 result existed: A wrong 25%, B wrong (actual 0.45 vs assumed 0.70), A wrong 45% with 25% missing records, and A *better* than assumed (0.95).
- **Data reuse caveat (same as v2):** these are not fresh, independent data. The evaluation rows' family IDs had counterparts in v1 calibration, and source seed independence is uncertified.
- Batches are formed from one frozen shuffle of the 21,004 evaluation pairs, in sizes 25, 100, 400 and all.

## Results: coverage (nominal 0.90), with mean set size in brackets

| Scenario | DNA only | v2 (no check) | v3, batch 25 | v3, batch 100 | v3, batch 400 |
|---|---|---|---|---|---|
| clean | 0.906 (2.02) | 0.901 (0.96) | 0.902 (0.98) | 0.901 (0.96) | 0.902 (0.98) |
| missing 25% | 0.906 | 0.904 (1.43) | 0.904 (1.44) | 0.904 (1.43) | 0.904 (1.44) |
| missing 70% | 0.906 | 0.906 (1.93) | 0.906 (2.01) | 0.906 (1.93) | 0.906 (1.93) |
| **A wrong 45%** *(seen)* | 0.906 | **0.757** (0.89) | 0.870 (1.67) | **0.905** (2.01) | **0.906** (2.02) |
| A wrong 25% *(new)* | 0.906 | 0.853 (0.93) | 0.865 (1.06) | 0.878 (1.39) | **0.906** (2.02) |
| B wrong *(new)* | 0.906 | 0.859 (0.94) | 0.880 (1.31) | **0.904** (1.96) | **0.906** (2.02) |
| A wrong 45% + missing 25% *(new)* | 0.906 | 0.822 (1.39) | 0.877 (1.74) | **0.905** (2.01) | **0.906** (2.02) |
| A better than assumed *(new)* | 0.906 | 0.947 (0.98) | 0.947 (0.99) | 0.947 (0.98) | 0.947 (0.98) |
| unknown origins | 0.906 | 0.906 | 0.906 | 0.906 | 0.906 |

Share of batches with fusion turned off, out of 841 / 211 / 53 batches at sizes 25 / 100 / 400:

| Scenario | batch 25 | batch 100 | batch 400 |
|---|---|---|---|
| clean (false alarms) | 1.9% | 0.5% | 1.9% (1 of 53) |
| A better than assumed | 1.1% | 0.5% | 0% |
| A wrong 45% | 70% | 99.5% | 100% |
| A wrong 25% | 12% | 41% | 100% |
| B wrong | 35% | 94% | 100% |

Full per-class metrics, z-values and per-source counts are in `results/v3/comparison.json`. Every fallback case produced exactly the DNA-only set.

## What improved

- **The v2 failure is fixed whenever a source is cited by enough cases.** With batches of 100 or more, coverage with a badly wrong source returns to about 0.905, the DNA-only level, compared with 0.757 in v2.
- **It held up on the three new wrong-source scenarios that v3 was not designed on.** Both milder and different-source errors are caught: B wrong is 94% detected at batch 100, and A wrong 25% is fully detected at batch 400.
- **No cost when sources are fine.** Clean-scenario results are essentially unchanged from v2, with a false-alarm rate of about 0.5–1.9% of batches. A source that is better than assumed is kept, so the efficiency gain stays (coverage 0.947, set size 0.98).

## What did not improve or remains weak

- **Small batches can't catch problems reliably.** With batches of 25, coverage under a wrong source is still 0.865–0.880, below nominal. With a mild error (A wrong 25%), even batches of 100 only reach 0.878. A source has to be cited by a few hundred cases before a mild error is reliably caught.
- **When a check rejects a source, the record information is lost.** Sets grow back to DNA-only size (about 2.0). v3 does not estimate a corrected reliability, so it cannot recover a "partly useful" source.
- **Heavy missingness plus small batches turns fusion off.** In the 70%-missing scenario at batch 25, 96% of batches had too few records to check, so the method fell back to DNA only. Coverage held, but set size rose from 1.93 to 2.01.
- **Only source-wide errors are detected.** A source that is reliable overall but wrong on specific cases is not caught.
- **The reference assumes evaluation cases look like calibration cases.** A different mix of cousin degrees could shift the residuals and change the false-alarm rate. That is untested.

## What remains unproven

- Behavior on fresh, independently seeded simulations, other relationship types, or real records. Records here are fabricated cousin-degree claims with invented reliabilities.
- Novelty. Estimating source reliability without labels (Dawid–Skene-style) and error-tolerant pedigree methods are existing related work.

## Reproduce

```bash
.venv/Scripts/python -m research.genetics.version3 freeze     # refuses if already frozen
.venv/Scripts/python -m research.genetics.version3 evaluate   # refuses if results exist or any frozen hash changed
.venv/Scripts/python -m pytest backend/tests research/genetics/tests -q
```

Verification on 2026-11-14: 61 tests passed (backend, research, v2 and the 9 new v3 tests). Evaluation took about 26 s on CPU. No AI calls, paid compute or real-person data were used.
