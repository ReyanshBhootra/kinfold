# Kinfold — Devpost draft

## Tagline
Every connection, a source. An evidence-linked genealogy research workspace that keeps contradictions visible.

## Inspiration
An appealing family story can outrun its evidence. We wanted a research assistant that makes each relationship inspectable, preserves inconvenient records, and explains why a lead remains possible or falls outside a stated constraint.

## What it does
Kinfold combines a disclosed synthetic unidentified-person case, simulated DNA-match summaries, and varied synthetic family records. The local engine extracts supported text patterns, builds a source-linked family graph, highlights conflicting dates and parent assertions, and evaluates candidate leads through explainable age, region, life-status and record-derived family-path criteria. Every cited assertion opens its original record and numbered excerpt. Leads remain unconfirmed.

New text evidence can change eligibility. Unsupported prose stays readable and is explicitly labeled without structured extraction. Research packs export the evidence, provenance fingerprints, findings, candidate reasons, next actions, audit log and versioned manifest. A local verifier checks citations, fingerprints and digest consistency; an independently saved digest supports change detection.

## How we built it
React, TypeScript and Vite power the investigation interface. FastAPI and Pydantic provide the API, bounded text ingestion, structured claims and citation validation. Atomic local JSON persistence keeps the demo runnable without accounts or keys. Separate synthetic evaluation families and evidence-perturbation tests check that decisions follow records rather than a hidden winner lookup.

Optional genuine adapters add Gemini structured **annotations**, a restricted deepagents plan/retrieve/extract/check/report loop, and MongoDB persistence. Model annotations remain separate from deterministic ranking; the live adapter is not arbitrary-document-to-pedigree reconstruction. Optional Solana devnet tooling submits only a namespaced SHA-256 digest to the Memo program and verifies actual confirmed transaction contents. It does not put names, DNA or source records on-chain.

## What we tested
Use the exact final counts and commands in docs/VALIDATION.md when submitting. The tests cover source spans, contradictory constraints, evidence-driven candidate changes, new leads, malformed parent assertions, prompt injection, upload continuation, persistence, exports and tampering. Browser checks exercise the actual API. deepagents executes its real harness against a scripted offline model; Gemini transport/schema and Mongo database contracts have offline tests.

## Challenges
The difficult boundary is between a source assertion and a conclusion. We kept conflicting claims instead of overwriting them, abstain when case estimates disagree, and flag malformed parent paths. We also separated a local checksum from a real on-chain anchor and a configured adapter from a successful live service run.

## Accomplishments
A complete local workflow works without keys: source records → cited relationships → explicit contradictions → explainable lead review → new evidence → changed constraints → verifiable research handoff. The interface exposes the evidence behind each step.

## What we learned
Evidence integrity does not establish evidence truth. A quote can be accurately located while its interpretation is still wrong. A shared-cM value can fit multiple relationship paths. Useful research tooling must make uncertainty and review requirements visible.

## What's next
Configure and record actual successful Gemini/deepagents/Atlas runs before claiming live use. With an explicitly configured development wallet, demonstrate a real Solana devnet anchor and independent transaction verification. Separately evaluate genetic inference using pedigree simulation/research methods with whole-family holdouts, declared baselines and abstention. No sequence-level inference or scientific calibration is claimed in this prototype.

## Submission accuracy notes
All people, records and DNA matches in the demo are synthetic. Candidate scores are heuristic, not identity probabilities. This is a local research prototype, not a validated forensic identification system. No live Gemini/Atlas/remote-model deepagents run or real Solana transaction has been verified during the offline build. Arlequin genetic genealogy eligibility needs organizer confirmation; no prize or eligibility is promised. Select sponsor technologies/categories based on the final demonstrated behavior and current organizer rules.
