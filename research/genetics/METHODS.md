# Experiment methods and validity limits

## Questions and claims

Primary question: how much do total shared cM and the source's IBD1 segment count distinguish **full1C–8C** in the supplied simulation, and how broad should supported hypothesis sets remain? Secondary question: under an explicitly fabricated record-error layer, what happens when copied statements are incorrectly counted as independent evidence, and which idealized claim should be verified next?

The histogram, split-conformal calibration, dependency grouping and information-gain concepts are existing methods. Parameters were fixed in implementation before inspecting their corresponding experiment outcomes; there was no external preregistration or test-set hyperparameter search. This is a reproducible baseline and sensitivity experiment, not a novel inference method or scientific discovery claim.

## Public data and QC

[Amy L. Williams' Zenodo dataset](https://zenodo.org/records/17489849), published2025-10-31, supplies Ped-sim cousin simulation definitions and summary files. Metadata lists CC BY4.0. The supplied README describes two batches of50,000 pairs per relationship and omits zero-sharing pairs from `.tot`; the downloaded definitions are checked for the expected copy count and cousin generation.

Only the16 odd-degree full-cousin `.tot` members per crossover model are selected: degrees3,5,…,17 correspond to1C,…,8C. Four models are examined: `ss_intf`, `sa_intf`, `ss_poiss`, `sa_poiss`. No raw genome/VCF or `.seg` member is fetched. Each source file's exact schema, unique ID space, generation/pedigree prefix, finite nonnegative numbers, integral IBD1 segment count and `total≈IBD1+2×IBD2` are validated. Rounding tolerance is explicit in code.

Absent IDs within the documented1…50,000 universe are restored as `(total=0, IBD1_segments=0)`, not as unrelated labels. One source row (`sa_intf`,4C,batch1,replicate23138) reports total0 with segment count1. It is recorded as unresolved QC exclusion, never silently changed or imputed. A possible rounding/zero-length cause is a hypothesis, not established from summaries.

The supplied `n_seg` counts **IBD1** segments only. No maximum segment length is available here. All selected positive rows happened to have IBD2=0; that does not establish an absence of IBD2 in other relationships/populations.

## Split provenance

Source `.tot` row order comes from awk associative iteration; random row splitting would be inappropriate. We parse the replicate integer and assign the group `(cousin_number, replicate_number)` using SHA-256 with salt `kinfold-genetics-v1`, modulo10,000. Values0…5999 are training,6000…7999 calibration,8000…9999 test.

Training/calibration use only `ss_intf` batch1 with their respective disjoint groups. Evaluation uses batch2 of every model, test groups only. Batch and crossover model are intentionally excluded from the group key, so matching source IDs cannot leak across partitions even if separate runs reuse identifiers or random streams. All400,000 group assignments are exported, compressed deterministically, and hashed. No test-based tuning occurs.

[Ped-sim documentation](https://github.com/williamslab/ped-sim) describes replicate pedigrees with different founders/randomized sex assignments. The archive does not supply RNG seed logs, so independence of random streams across source runs cannot be certified. This conservative group split mitigates matching-ID leakage; it does not prove every possible dependence absent.

## Baselines and prediction sets

Four histogram methods are fitted: total cM alone, and total cM plus IBD1 segment count, each in an unconditional cohort including restored zeros and a separately fitted positive-sharing cohort. Positive-only training/calibration are explicitly conditional on nonzero sharing. This is important because distant relatives are mostly absent from observed-match summaries.

Total cM uses a separate zero bin and fixed `floor(log1p(cM)/0.18)` positive bins (capped at50); segment counts are capped at80. Additive pseudocount0.1 is fixed. Counts are normalized per class, then combined with a declared uniform eight-class reference prior. The positive-only prior is uniform among those classes **conditional on sharing**, not a real population prior. Source positive cohorts are imbalanced, so macro class accuracy is reported alongside cohort-weighted accuracy.

For each class, calibration nonconformity is `1−reference_score(true_class)`. The threshold is the `ceil((n+1)×0.9)`-th ordered calibration score, infinity when that rank exceeds n. A candidate class is included when its nonconformity is no larger than its class threshold. The method issues a single degree only for a singleton set; multi-class and empty sets abstain. This uses standard class-conditional split-conformal reasoning, whose guarantee requires class-conditional exchangeability. Crossover-model shifts and data selection can break that assumption. Small distant-cousin calibration counts are explicitly reported.

Metrics include full8×8 confusion matrices, top-choice accuracy, macro accuracy, true-class set coverage, set-size distribution, singleton accuracy/issuance, abstention, empty sets and Brier score within the declared simulation prior. Baselines are uniform random expectation12.5% and always1C. No unrelated-control performance, identity accuracy or population calibration is claimed. See the [conformal tutorial](https://arxiv.org/abs/2107.07511) and [conditional-coverage literature](https://arxiv.org/abs/2305.12616) for existing methodology.

## Fabricated record/error extension

This begins only after the genetic pipeline runs. Two simulated original sources directly assert a cousin class. Their assumed/nominal correctness rates are0.85 and0.70, otherwise choosing uniformly among the other classes; each is nominally missing with probability0.25. These are engineering stress parameters, not empirical document quality. Labels drive the artificial observation generator, but inference/selection functions receive no truth label. The deterministic RNG seed and scenarios are published in `record_stress_config.json`.

Nominal fused calibration uses positive-sharing calibration groups from `ss_intf` batch1. The test uses positive-sharing batch2 test groups, up to1,000 per class selected by a separate stable hash; its6,376-case distribution differs from the full41,750 positive cohort. Do not compare their aggregate accuracy as if they were the same sample.

Naive fusion multiplies each document's assumed class likelihood. Provenance grouping counts a known internally consistent origin once; conflicting known-origin bundles and unknown lineage contribute no likelihood weight. Both methods use nominal single-copy fused calibration thresholds. Test scenarios alter missingness, copy count, source reliability or lineage visibility **without recalibration**. Hard intersection with every record assertion is a separate brittle baseline. Full metrics and failures are retained.

The unknown-lineage version returns DNA scores but still uses fused thresholds. Its coverage failure is a calibration/fallback design defect, not evidence that ignoring unknown sources is intrinsically harmful. A full DNA-score/DNA-threshold fallback or missingness-conditional calibration is a future change requiring fresh evaluation; it is not retrofitted to improve these results.

The next-question policy maximizes binary entropy of whether a record's asserted class is true under the current reference scores. It compares first-available choice with an evaluation-only truth-aware oracle upper bound. The verification answer is assumed perfectly accurate and directly degree-informative. Larger log-loss recovery can simply mean a worse starting score model; compare selection policies within the same model, not raw gains across models. This does not validate real record selection, verification costs or real-world information gain.

## Out-of-scope and integration boundary

No unrelated/half/removed/lineal/avuncular or endogamy controls, consumer segment detection threshold, genotype error model, real people, raw DNA, real historical records, full-pedigree reconstruction, field reliability estimates or scientific identification validation are present. There is no deployment recommendation. Nothing is connected to production Kinfold scoring. A broader hypothesis set and independently validated record constraints are required before considering integration.

This is an exploratory secondary study formed after inspecting the genetic baseline, reusing a capped subset of the same held-out genetic group pool. It is not a fresh confirmatory replication. The JSON configuration files document the fixed protocol; they are not general-purpose parameter inputs. To change the protocol, version the implementation and snapshot together and evaluate on fresh untouched data.
