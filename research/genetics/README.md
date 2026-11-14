# Standalone genetic uncertainty research

This is a CPU-only, model-free research prototype, separate from Kinfold's production app and ranking. It uses public Ped-sim simulation summaries. It does not identify real people, reconstruct full pedigrees, train on real genotypes, or establish scientific novelty.

## Reproduce from the application repository

Use the existing Python environment. There are no new runtime dependencies; tests use the already installed pytest.

```powershell
.venv/Scripts/python -m research.genetics.download
.venv/Scripts/python -m research.genetics.benchmark
.venv/Scripts/python -m research.genetics.record_experiment
.venv/Scripts/python -m research.genetics.make_report
.venv/Scripts/python -m pytest research/genetics/tests -q
```

On macOS/Linux use `.venv/bin/python`. First download selectively fetches roughly18 MB of compressed `.tot` summaries; raw segments/genomes and the2.2 GB archive collection are not downloaded. The40 MB network budget is enforced; a server ignoring byte ranges causes refusal, not a silent full download. Cached reruns still fetch archive directories and verify cached CRC/SHA evidence. `cache/` and `results/` are ignored by Git; deliverable reports are also copied to the build-chat outputs.

The definition archive's published MD5 is verified. Summary members are checked against ZIP CRC/length and pinned locally with SHA-256. Full segment-archive MD5s are recorded but **not verified** because those archives were not fully downloaded. HTTPS/member checks are not a substitute for a verified full-archive checksum.

Read [METHODS.md](METHODS.md), [FINDINGS.md](FINDINGS.md) and [ATTRIBUTION.md](ATTRIBUTION.md) before interpreting results. Machine outputs: `results/benchmark.json`, `results/record_stress.json`, `results/models.json`, and `results/split_groups.csv.gz`. `cache/data_manifest.json` records every selected member, source hash, archive offset/checksum and validated definition count.

## Restricted simulation example

```powershell
.venv/Scripts/python -m research.genetics.predict --cm 220 --ibd1-segments 12
```

This only compares full first-through-eighth cousins using a declared uniform reference prior. It cannot determine whether a pair belongs to that scope. Half cousins, removed cousins, close/lineal/avuncular relationships, unrelated people and endogamy are absent. A high reference score is not a forensic probability. The production demo contains other relationship types; this classifier must not be used to validate its illustrative shared-cM values or candidate graph.

## Separate record stress test

The genetic summaries are from the cited public simulator. The added records, missingness, reliability values and perfect verification oracle are **fabricated stress assumptions**, not historical data or measured reliability. Their purpose is to expose dependence/calibration failures. The record layer directly states a cousin class and is much simpler/more informative than real birth registers, obituaries or genealogy documents. It is not evidence of real-record effectiveness.

Known-copy grouping behaves as expected, but the tested version loses coverage under missingness, wrong reliability assumptions and unknown provenance. In particular, returning DNA-only scores while retaining fused-record thresholds is not a valid full fallback. These failures are preserved in the reports rather than corrected after seeing the test results. Do not deploy this extension or claim a coverage guarantee from it.

No paid compute, active AI/model service, account, wallet or live-provider credential is used. No production data/ranking/UI was changed.
