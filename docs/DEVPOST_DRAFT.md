# KinFold: Devpost draft

> Placeholders marked **[DECIDE]** need a human decision before submission (see the linked issues). Remove this note, the checklist and every placeholder before you paste the copy into Devpost.

## Submission checklist (Devpost fields → where the text is)
1. **Project name:** `KinFold`
2. **Tagline / elevator pitch** (Devpost limits it to about 200 characters): copy "Tagline" below.
3. **Thumbnail / gallery images** (3–5 screenshots, 3:2 works best):
   - the family graph with the case summary;
   - Candidate leads, showing the three leads excluded by DNA;
   - the AI extraction findings, with a rejected claim and its reason;
   - Lena Hale "Found by Kinfold" and DNA consistent;
   - the agent run panel;
   - the Lead timeline with "On-chain: transaction found on devnet".
4. **About the project:** Devpost's story fields. Paste "Inspiration", "What it does", "How we built it", "Challenges", "Accomplishments", "What we learned" and "What's next" into the matching boxes. Keep "Accuracy notes" at the end of the story.
5. **Built with** (tags): copy the tag list under "Built with".
6. **"Try it out" links:**
   - GitHub: https://github.com/ReyanshBhootra/kinfold (public);
   - the Solana Explorer link for the Hale-state anchor (under "Built with").
   - There's no hosted demo; it runs locally (README → "Run locally").
7. **Video demo link:** YouTube or Vimeo URL from #5, at most 2 minutes. Devpost needs a public or unlisted link.
8. **Prize tracks / opt-in prizes:** select exactly the tracks under "Prize tracks". Add Arlequin only if the sponsor confirms (#4).
9. **Team members:** add both teammates' Devpost accounts so both are on the submission.
10. **Submit before 08:00 ET.** Devpost lets you edit after submitting, until the deadline.

## Tagline
No link goes unchecked. KinFold tests every family-tree lead against the DNA and ties each step to the exact record line behind it.

## Inspiration
In forensic genetic genealogy, a tidy family story can run ahead of its evidence. A DNA match and a few records point at a family, and a researcher fills in the rest. We wanted a tool that does the opposite: it tests the story against the numbers, keeps contradictions visible, and makes every relationship traceable to the exact line of the record behind it.

## What it does
Kinfold works on a disclosed, fully **synthetic** unidentified-person case. An unknown person shares 220 cM of simulated DNA with Ruth Mercer, and the case records point at three of Ruth's nieces.

1. **The DNA says no.** Kinfold builds a family graph from the records. Every edge cites a document line span. It then follows the recorded parent links from each lead to the DNA match. Under the recorded pedigree, all three leads would be Ruth's nieces, with an expected 1,201–2,282 cM, against 220 observed. All three are excluded, and each also has record-based reasons: a birth year outside the estimated range, an alive record after the estimated death, or conflicting birth sources. The first suggested next step is to search branches that fit 220 cM.
2. **The AI reads messy records, and must quote them.** We upload two new synthetic records: an obituary and a 1972 birth announcement. Gemini proposes typed claims (birth, death, parent, spouse, sibling), each with a quote and a line span. Kinfold accepts a claim only if the quote is verbatim in the cited lines and names every person and year the claim asserts. In our recorded run, Gemini proposed 13 claims. Kinfold verified 11 and rejected 2, and the UI shows each rejection with its reason. Both rejections are conservative: the record arguably implies the claim, but the quote doesn't state it. One said George Hale was alive in 2008, but the quote never states the year. The other claimed a marriage from a quote with no explicit marriage wording. Rejected claims never reach the graph.
3. **A new lead appears.** The verified claims link Frances Hale, Arthur Mercer's sister, to her granddaughter Lena Hale. Kinfold proposes Lena itself ("Found by Kinfold"). Her 1972 birth year falls inside the estimated range. Under the recorded pedigree she would be Ruth's first cousin once removed, with an expected 102–980 cM, so 220 cM is consistent. The record gives her birthplace only as "Cooper Hospital", so Kinfold awards no region point it can't support.
4. **An agent checks the lead.** A LangChain deep agent investigates Lena step by step. It searches and reads records, tests relationship hypotheses against the DNA, and submits claims to the same quote verifier. Kinfold computes every result, and the agent can't change any lead.
5. **Every lead gets a tamper-evident timeline.** One click anchors a hash of the current research state on Solana devnet. The hash covers the cited records, the AI's raw outputs and the lead decisions. If the evidence later changes, Kinfold says the current state differs from the anchor. Only the hash goes on-chain: no names, DNA or records.

Every finding opens the source record with the cited lines highlighted. Research packs export the records, source fingerprints, findings, candidate reasoning, audit log and a manifest digest, and a local verifier detects later changes.

## How we built it
- **Frontend:** React, TypeScript and Vite. The UI has an interactive family graph, a source reader with line highlighting, candidate review, uploads and the research log.
- **Backend:** FastAPI and Pydantic. A deterministic pipeline turns claims into relationships, findings and leads. Atomic local JSON storage keeps the demo runnable without accounts.
- **DNA check:** finds the closest common ancestors through recorded parent links. It compares observed shared cM with a reference range for that relationship: 99% Ped-sim intervals for first to third cousins, approximate Shared cM Project ranges otherwise. It's a range-consistency check, not a likelihood.
- **Gemini extraction:** `gemini-3.5-flash` with structured JSON output. Strict Pydantic models validate the reply, and a separate verifier checks each quote against the document. Every real response is recorded with its model and timestamp, so the demo can replay it offline and re-verify it, clearly labelled "replay of a recorded response". We never fabricate a live AI result.
- **Lead investigator (LangChain deepagents):** a restricted `create_deep_agent` harness investigates one lead at a time. It plans, searches and reads records, tests DNA hypotheses against reference ranges, submits claims to the same quote verifier, proposes next steps and writes a cautious report. Kinfold's own tools compute every result; the agent only chooses what to check. It cannot change lead statuses, and identity claims in its report are refused. Each run's decisions are recorded and replayed with every result recomputed. In our recorded live `gemini-3.5-flash` run, the agent:
- read all 12 records;
- tested 7 relationship hypotheses against 220 cM (4 fit, 3 didn't);
- had 7 of 8 claims verified, then fixed the rejected one;
- rewrote its report after Kinfold refused the first draft as too long.
- **Lead timeline (Solana devnet):** the manifest digest goes into a Memo transaction through our CLI. The app stores an anchor only after the transaction is confirmed and its memo checked on-chain, and **Verify** re-checks it later.
- **Storage:** MongoDB Atlas (verified on a real cluster), or local JSON.
- **Safety:** uploaded documents are treated as untrusted evidence, never as instructions. Tests cover prompt injection.

## Challenges
- **Live Gemini rejected our strict response schemas** (`additionalProperties`, `$ref`, nullable `anyOf`) with 400 errors, which our offline tests couldn't catch. We now send Gemini a simplified OpenAPI-subset schema and still validate replies against the original strict models, so nothing is loosened on our side.
- **Deciding what counts as "supported".** A quote can be located exactly and still not support the claim built on it. Our verifier prefers to drop a true claim rather than accept an unsupported one, and it shows every rejection.
- **Keeping heuristics honest.** Lead scores are labelled heuristic evidence scores, never probabilities. "DNA consistent" means inside a reference range under the recorded pedigree, nothing more.

## Accomplishments
- The DNA check overturns the obvious story, and the AI step finds a branch that fits. Each step cites the exact lines it relies on.
- AI claims are proposals until they pass verification, and rejected claims stay visible.
- The full workflow runs offline, without keys, replaying a real recorded Gemini run.
- If a live Gemini call fails mid-demo, Kinfold falls back to the real recorded response and says so.

## What we tested
- Backend test suite (pytest): source spans, contradictions, evidence-driven candidate changes, DNA ranges, extraction verification, the Gemini schema regression, prompt injection, uploads, persistence and exports.
- `scripts/evaluate.py`: two held-out synthetic families with 6 candidate decisions. The full engine got 6/6 against 4/6 for a birth-range-only baseline. That's a small correctness check, not scientific validation.
- `npm run test:integration`: runs against the real HTTP API. It locates every citation, checks digests across Python and JavaScript, uploads a record and confirms that an old digest no longer matches.
- `pytest backend/tests research/genetics/tests`: **101 passed**. `npm run build`, `npm run test:anchor` (4) and `npm run test:package` (3) also pass. Re-run on the final commit before submitting if anything changes.
- **Live runs, all recorded in `docs/VALIDATION.md`:** Gemini extraction and annotations, the deep agent's investigation, MongoDB Atlas persistence, and three Solana devnet anchors.

## What we learned
Evidence integrity isn't evidence truth. A shared-cM value fits several relationships, and a perfectly located quote can still be misread. Useful research tooling shows its uncertainty and leaves the conclusion to a human reviewer.

## What's next
- Better name linking, for example "Patricia Hale" and "the former Patricia Novak".
- Relationship inference evaluated on simulated pedigrees with whole-family holdouts and declared baselines (`research/genetics/`).

## Built with
Tags: `react`, `typescript`, `vite`, `python`, `fastapi`, `pydantic`, `google-gemini`, `langchain`, `deepagents`, `mongodb-atlas`, `solana`, `node.js`.

- **MongoDB Atlas:** case storage. Verified on a real Atlas cluster; the case survives a full app restart with an identical evidence digest.
- **Solana devnet:** the lead timeline. Verified anchor of the Hale state (Lena Hale possible): https://explorer.solana.com/tx/4qWrFgPTGC8wxif392icaBQM7ijpqc289k48GWndCpMFhM4q4k3yZ5MfAwEoVBrE9qeMuN3q9BCHbTj48jRWpwFV?cluster=devnet

## Prize tracks
- **Best Use of Gemini AI:** real `gemini-3.5-flash` extraction, recorded on 2026-11-14 and replayed and re-verified in the demo.
- **[DECIDE: Arlequin AI-Driven Forensics, #4]** We've emailed the sponsor and are waiting for an answer. List it first only if they confirm the project fits.
- **MongoDB Atlas:** cases persist in Atlas, verified with a real cluster. This is storage only, so describe it plainly.
- **Solana:** "Every lead gets a tamper-evident timeline". Real devnet Memo anchors of each research state, verified on-chain from the app (Explorer link above). An anchor proves the state existed unchanged; it doesn't prove the records are true.
- **LangChain "Best use of deepagents":** a deep agent that plans and investigates a lead with real forensic tools. Deterministic code recomputes every conclusion, so the run is replayable. A live `gemini-3.5-flash` run is recorded in `data/agent_runs/`.
- **Amazon "Best Practical AI":** the agent reasons, plans and takes multi-step actions. Its tools are bounded, every step is in a cited audit trail, and it has no ability to change outcomes.

## Demo video
**[DECIDE: link from #5]** Not recorded yet.

## Accuracy notes (keep in the submission)
- All people, records and DNA matches are synthetic. Kinfold identifies no one.
- Lena Hale is a research lead, not an identification. DNA consistency is a range check on a recorded pedigree, not a likelihood. Evidence scores are heuristic, not probabilities.
- The AI step in the demo is a replay of a real recorded Gemini response, labelled as such in the UI.
- On-chain status is shown only for a confirmed Solana devnet transaction of the current evidence digest; otherwise the screen says "not anchored". An anchor proves a state existed unchanged, not that the records are true.
- The agent step in the demo is a replay of a real recorded agent run, with every result recomputed, and it's labelled as such.
- This is a hackathon research prototype, not a validated forensic system.
