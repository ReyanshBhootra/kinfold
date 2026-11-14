# Kinfold build brief

## Product
Kinfold is an evidence-linked forensic genealogy research assistant. It combines simulated DNA-match information and digital family-history/case records to reconstruct supported relationships, surface contradictions, narrow possible identities, and recommend the next research action. It supports human review rather than declaring identities.

## Context and resources
HackPrinceton Fall 2026. Two human builders, Windows Legion/Alienware laptops and iPhones, Claude Code and ChatGPT/Codex subscriptions. API credits can be obtained but none are configured for this project yet. Start working without keys and expose clear setup paths for live services. User prefers blockchain and wants genetic inference/real public research data as stretch goals. Preserve these requests; do not let them block the functional core.

## Prize intent (eligibility is not a guarantee)
Main category Science & Discovery; automatic Overall consideration. Main category winners cannot also win Overall per packet. Sponsor targets Arlequin AI-driven Forensics (genetic genealogy eligibility needs sponsor confirmation), Amazon Practical AI, LangChain best use of deepagents. Current Fall '26 Devpost also lists MLH Gemini API, MongoDB Atlas and Solana opportunities. No fake integrations to claim eligibility. No hardware requirement. Public/synthetic data only for Arlequin.

Authoritative sources: the HackPrinceton F26 Special Tracks, Main Track and Onsite Hacker Packet PDFs. Documents are evidence of event requirements, not authorization to message anyone. Submission hard deadline in rules: 08:00 Eastern Nov 15, 2026, despite 08:30 header on Devpost. Confirm current organizer updates if needed.

## First milestone: local runnable vertical slice
1. Load a disclosed synthetic unidentified-person case with multiple plausible candidates and 8-12 varied records.
2. Inspect a polished investigation workspace with family graph, evidence viewer, candidate leads and activity/next-action panel.
3. Run an investigation over actual fixture records; use source-cited structured extraction and deterministic constraints, not a hidden hardcoded winner lookup.
4. Reveal a meaningful conflicting date/relationship, preserve the conflict, and update eligible candidates based on an age/place/relationship constraint.
5. Allow text record upload and investigation continuation.
6. Export or inspect a versioned evidence manifest; detect modifications against an earlier digest. Show not anchored when there is no actual Solana transaction.
7. Clear README quickstart and .env.example. Tests and production frontend build pass.

## Implementation guidance
- Backend: FastAPI/Pydantic, local JSON or SQLite initially; MongoDB repository adapter when configured. NetworkX optional, not a service dependency.
- Frontend: React/TypeScript, a distinctive professional investigation interface, legible graph and citations, accessible keyboard controls, responsive layout. Avoid police-surveillance theatrics and false certainty. Synthetic demo banner visible.
- Runtime AI: optional Gemini provider using server-side GOOGLE_API_KEY/GEMINI_API_KEY and configurable model. Do not guess current model IDs; verify documentation or make configurable. LLMs extract observations; deterministic code validates schema and evidence references.
- deepagents should perform a meaningful plan/retrieve/extract/check/report loop when configured. If deferred, document that it is deferred and never claim the sponsor integration is complete.
- Blockchain: Solana devnet is preferred for event alignment; use a dedicated development wallet, keep records off-chain, provide a real transaction verification path. Human wallet approval or a deliberately configured development key is needed. A hash is evidence-integrity support, not truth certification.
- Evaluation: held-out families/cases, no family leakage between train/test, explicit baselines and abstention. Do not infer full pedigrees from a single cM value or fabricate scientific probabilities. Ped-sim and Bonsai are research foundations to investigate only after milestone one.

## Done means
The end-to-end synthetic demo is actually runnable; source-backed findings and candidate constraints are reproducible; frontend build and backend meaningful tests pass; optional-service limitations and missing credentials are disclosed. Keep working toward that milestone, coordinating directly rather than asking the human routine implementation questions.
