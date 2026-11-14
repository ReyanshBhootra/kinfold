# Genetic research findings — bounded prototype

The public-data baseline and an explicitly fabricated record-dependence stress test are implemented and reproducible. **No new genetic discovery or established novelty is demonstrated.** Production Kinfold is unchanged. These are simulation-restricted results, not identification/forensic accuracy.

## Data feasibility and provenance

Source: Amy L. Williams, Zenodo DOI10.5281/zenodo.17489849 (2025-10-31), CC BY4.0. Only64 full-cousin `.tot` members were range-fetched across four crossover models, about18 MB compressed from otherwise2.2 GB of archives. No raw segments/genomes or real-person data were collected. Definitions' published MD5 and all member CRC/length checks pass; full segment-archive MD5s remain unverified. Local source SHA-256s and all400,000 group split assignments are supplied.

The selected files contain1,662,958 positive source rows in3.2 million documented pair slots. Omitted zeros are restored only within validated replicate IDs/counts. One total0/segment-count1 source row is preserved as QC exclusion. Seed logs are absent, so source random-stream independence is not certified. Matching relationship/replicate IDs are grouped together across model/batch names.

## Genuine genetic-summary baseline

Train/calibrate: disjoint hash groups in ss_intf batch1. Test: a third disjoint group in batch2. Parameters were implementation-fixed, with no test tuning or external preregistration. The prior is uniform among full1C–8C within the declared cohort. Unrelated and other relationship types are outside scope.

| Cohort / method | N | Top-choice accuracy | Macro class accuracy | True-class set coverage | Mean set size | Abstain from one degree |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cm_unconditional | 79,546 | 51.90% | 51.86% | 94.42% | 3.198 | 74.30% |
| cm_segments_unconditional | 79,546 | 53.10% | 53.06% | 93.78% | 3.132 | 71.13% |
| cm_positive_only | 41,750 | 68.06% | 47.21% | 92.48% | 2.255 | 53.08% |
| cm_segments_positive_only | 41,750 | 72.87% | 49.65% | 90.26% | 1.968 | 45.17% |

Uniform random expectation is12.5%; always1C achieves24.16% in the imbalanced positive-sharing cohort. The positive-sharing weighted72.9% result should **not** be advertised as general genetic accuracy: macro accuracy is49.65%, and close cousins dominate that cohort.

The distant-cousin limitation is substantial. Positive8C training/calibration counts are314/96. In the83 positive8C test cases, top-choice accuracy is0%; set coverage is89.16% with a mean4.52 hypotheses. No positive5C–8C test case receives a singleton degree. The zero-sharing mass is not converted to an unrelated label.

### Crossover shift: no blanket coverage guarantee

| Test model | Positive-sharing N | Joint-method set coverage (nominal90%) | Mean set size |
| --- | ---: | ---: | ---: |
| ss_intf | 41,750 | 90.26% | 1.968 |
| sa_intf | 41,958 | 92.05% | 1.982 |
| ss_poiss | 40,894 | 86.43% | 1.918 |
| sa_poiss | 41,190 | 88.07% | 1.944 |

The ss_poiss coverage drop to86.43% is a negative result: the nominal calibration target does not survive this simulation-model shift. No threshold was retuned on these tests.

## Fabricated record/dependency stress — not historical evidence

This separate6,376-case capped positive-sharing cohort uses artificial statements that directly assert a cousin class. Correctness/missingness parameters and perfect verification answers are invented stress assumptions, not learned reliability or biological realism. DNA-only accuracy in this differently balanced cohort is60.68%; it must not be compared with72.87% above as a degradation on the same sample.

| Scenario | Naive independent-copy coverage | Known-origin grouped coverage | Hard-filter true-degree retention |
| --- | ---: | ---: | ---: |
| nominal_single_copy | 89.84% | 89.84% | 62.66% |
| missing_70_percent | 80.49% | 80.49% | 78.42% |
| A_copied_six_times | 83.94% | 89.84% | 62.66% |
| A_wrong_rate_45_percent_copied_six_times | 60.90% | 81.04% | 46.47% |
| A_copied_six_times_lineage_unknown | 83.94% | 73.60% | 62.66% |

Known copies give the expected dependence lesson: grouping preserves the nominal scenario's result, while multiplying copies as independent observations degrades retention. This is an existing principle, not evidence of novelty or real-record effectiveness.

**Failures are retained.** Missing70% records reduces grouped coverage to80.49%; worse-than-assumed source reliability reduces it to81.04%. Unknown lineage reduces it to73.60%. That last case exposes a design defect: the prototype falls back to DNA-only scores but keeps thresholds calibrated for fused records. Unknown provenance must not be described as safely handled merely because likelihood weights are ignored. A full DNA/DNA-threshold fallback or conditional calibration is future work, requiring fresh test evaluation.

### Idealized next-question experiment

The policy chooses a binary degree-claim correctness question by entropy. Truth is used only by an evaluation oracle. This assumes a perfect, directly informative verification answer and does not model real record retrieval, costs, ambiguity or linkage errors.

| Nominal scenario / same starting model | Mean true log-loss recovery (nats) |
| --- | ---: |
| First available record | 0.15769 |
| Entropy-selected record | 0.16876 |
| Truth-aware oracle upper bound | 0.17302 |

The observed selection improvement is modest and entirely within a fabricated oracle task. Comparing log-loss recovery across different starting score models would be misleading: a badly overconfident model can have much more loss available to recover. No real-world next-action benefit or optimality is established.

## What this supports and what it does not

We have a working public-data parser, provenance trail, leak-resistant split, empirical baselines, honest uncertainty sets, shift tests and a controlled source-dependence stress harness. The concrete useful outcome is knowing which assumptions fail before putting a genetic score into the app. The production demo's generic genealogy relationships must not be validated by this full-cousin-only model.

There is no biological discovery, publication-level novelty, validated pedigree reconstruction, unrelated-control performance, population posterior, field-calibrated document reliability or forensic identification result. Existing Bonsai, repare, FIGGsolver and conformal-prediction work preclude broad invention claims. See ATTRIBUTION.md.

A defensible next experiment would pre-specify full uncertainty fallback/missingness calibration, obtain independent seeded simulations with broader relationship controls, use indirect record constraints rather than direct class labels, and evaluate on a fresh untouched split. Source-lineage uncertainty and imperfect verification need explicit models. Do not claim that the present grouped method solves those cases.

## Reproduction and checks

Run the commands in README.md. Machine reports include confusion matrices, per-class outcomes, all source hashes, split hash/counts, calibration sizes, QC exclusions and assumptions. Unit fixtures are visibly fabricated schema/plumbing examples only; they are never used as biological benchmark data. No new dependencies, model calls, paid compute, private data or production-ranking changes were used.

Final checks: `.venv/Scripts/python -m pytest backend/tests research/genetics/tests -q` passed **41 tests** (21 production/backend plus20 research tests). Upstream optional LangSmith emits13 Python3.14 deprecation warnings; no warning suppression added. The final cached rerun took about11.81 seconds for the genetic benchmark and3.47 seconds for the record stress test on this machine; download/network time is separate. A primary API health check still returns ok/demo/JSON storage with all live provider flags false. No production-ranking files were modified.
