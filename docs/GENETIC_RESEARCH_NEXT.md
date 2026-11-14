# Genetic inference: preserved stretch work

The running application uses a disclosed simulated shared-cM summary and record-derived family paths. It does not infer a genetic relationship distribution, process DNA sequences/VCFs, or validate an identity. The current two-case held-out check evaluates deterministic record reasoning only.

For a separate experiment, [Ped-sim](https://github.com/williamslab/ped-sim) provides pedigree/genetic-transmission simulation, and [Bonsai](https://github.com/23andMe/bonsaitree) provides pedigree reconstruction research code. The [Bonsai paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8595950/) is the methodological starting point. Neither package is integrated or claimed as part of this demo.

The practical next milestone is to simulate many independent families, split by whole founder pedigree before any fitting or tuning, and keep held-out families/IBD summaries separate from runtime candidate inputs. Compare record-only constraints, a declared genetic baseline, and combined evidence. Measure relationship-set coverage, incorrect exclusions, abstention and calibration where genuine likelihoods exist. Keep citation accuracy as a separate measure. A single cM value must support multiple possible relationship paths rather than a fabricated exact pedigree or confidence percentage.

Any public research dataset integration needs an explicit dataset choice and provenance/license review before ingestion. Do not source private profiles, genealogy accounts or private DNA. No real-person data has been collected for this build. Sponsor confirmation is still needed for genetic genealogy under Arlequin; no prize or eligibility claim follows from this roadmap.
