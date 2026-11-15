# KinFold: Devpost draft

> Placeholders marked **[DECIDE]** need a human decision before submission (see the linked issues). Remove this note, the checklist and every placeholder before you paste the copy into Devpost.

## Submission checklist (Devpost fields → where the text is)
1. **Project name:** `KinFold`
2. **Tagline / elevator pitch** (Devpost limits it to about 200 characters): copy "Tagline" below.
3. **Thumbnail / gallery images** (3–5 screenshots, 3:2 works best):
   - Case overview with the storyline (all steps checked) and the family tree;
   - Candidate leads: Lena Hale's card with the green DNA bar, and the compact excluded leads;
   - Clara Mercer's card opened, with the "doesn't fit" DNA bar;
   - Findings filtered to "AI reads", showing a rejected claim and its reason;
   - the agent investigation opened, with the 7-hypothesis DNA chart;
   - Case activity (handoff view);
   - Evidence integrity, with the Lead timeline showing "On-chain: transaction found on devnet".
4. **About the project:** Devpost's story fields. Paste "Inspiration", "What it does", "How we built it", "Challenges", "Accomplishments", "What we learned" and "What's next" into the matching boxes. Keep "Accuracy notes" at the end of the story.
5. **Built with** (tags): copy the tag list under "Built with".
6. **"Try it out" links:**
   - GitHub: https://github.com/ReyanshBhootra/kinfold (public);
   - the Solana Explorer link for the Hale-state anchor (under "Built with").
   - There's no hosted demo; it runs locally (README → "Run locally").
7. **Video demo link:** YouTube or Vimeo URL from #5, at most 2 minutes. Devpost needs a public or unlisted link.
8. **Prize tracks / opt-in prizes:** select exactly the tracks under "Prize tracks", starting with **Arlequin (AI-Driven Forensics)**, which the sponsor confirmed (#4).
9. **Team members:** add both teammates' Devpost accounts so both are on the submission.
10. **Submit before 08:00 ET.** Devpost lets you edit after submitting, until the deadline.

## Tagline
No link goes unchecked. KinFold tests every family-tree lead against the DNA and ties each step to the exact record line behind it.

## Inspiration
In 2014, an innocent filmmaker became a suspect in a murder case. Not because of his DNA: his father's DNA, sitting in a genealogy database, came close to the killer's, and investigators followed the family line to him. His own DNA cleared him. ([PBS NewsHour](https://www.pbs.org/newshour/show/a-father-took-an-at-home-dna-test-his-son-was-falsely-accused-of-murder))

That's forensic genetic genealogy at its most fragile. When police have DNA but no name, genealogists find the unknown person's distant cousins in public DNA databases and build their family trees backwards until one person fits. It caught the Golden State Killer in 2018, and a public registry counts more than a thousand publicly disclosed cases since. ([Genealogy Explained](https://www.genealogyexplained.com/blog/the-figg-blog-a-recap-of-2023-nine-years-of-figg/)) About **16,000** people in the U.S. are still unidentified. ([NamUs, May 2026](https://namus.nij.ojp.gov/sites/namus/files/media/document/namus-stats-all-may-2026.pdf))

But a family tree is only as strong as its weakest link, and the links are usually a researcher's reading of old records. Add AI that writes confident family trees, and one wrong link can point at the wrong person. We wanted a tool where **no link goes unchecked**: every relationship tied to the exact line of a record, every lead tested against the DNA, and every AI claim treated as a proposal until a quote proves it.

## What it does
KinFold works on a disclosed, fully **synthetic** unidentified-person case. An unknown person shares **220 cM** of simulated DNA with Ruth Mercer, and the records point at three of Ruth's nieces.

1. **The DNA says no.** KinFold builds the family tree from the records, with every edge citing a line span, and follows the recorded parent links from each lead to the DNA match. All three would be Ruth's nieces, who usually share **1,201–2,282 cM**. They share 220. All three are excluded, with the reason drawn on screen as a DNA range bar, plus record-based reasons (a birth year outside the estimate, an alive record after the estimated death, conflicting birth sources).
2. **The AI must quote its sources.** We add two messy records, an obituary and a 1972 birth announcement. Gemini proposes typed claims, each with a quote and line span. KinFold keeps a claim **only if the quote is word for word in those lines and names every person and year** it asserts. In our recorded run, Gemini proposed 13 claims: **11 verified, 2 rejected**, each shown with its reason. Both rejections were probably true, but the quote didn't say it, and we'd rather lose a true claim than trust an unsupported one. Rejected claims never reach the tree.
3. **A new lead appears.** The verified lines reveal a branch nobody named: Frances Hale, Arthur Mercer's sister, and her granddaughter **Lena Hale**. KinFold proposes Lena itself ("Found by Kinfold"): born in 1972, inside the estimated range, and as Ruth's first cousin once removed she'd usually share **102–980 cM**, so 220 fits. Her birthplace is only "Cooper Hospital", so KinFold awards no region point it can't support.
4. **An agent double-checks the lead.** A LangChain deep agent investigates Lena: it reads the records, tests **7 relationship hypotheses** against the DNA (4 fit, 3 don't), and submits claims to the same quote verifier (**7 of 8 verified**; it fixed the rejected one). KinFold's own code computes every result, and **the agent can't change any lead**.
5. **Every lead gets a tamper-evident timeline.** One click anchors a hash of the current state (cited records, the AI's raw outputs, lead decisions) on **Solana devnet**. If the evidence changes later, KinFold says the current state differs from the anchor. Only the hash goes on-chain: no names, DNA or records.

**Built for the people who'd use it:**
- **Case activity is a handoff view:** who worked on the case, what each person did, where it stands and the next steps, so a case can pass between investigators without losing the thread. Every step in the audit trail is logged under the researcher's name. In this prototype that's a self-declared display name, not a sign-in.
- **Evidence library as colour-coded folders**, organised by record type, year, place or review progress, plus personal folders ("Shippy's review").
- **Family-tree spotlight:** click anyone to light up their recorded branch, with each relationship and its sources.
- **Research packs** export records, source fingerprints, reasoning, audit log and a manifest digest, and a local verifier detects any later change.

## How we built it
- **Frontend:** React, TypeScript and Vite. Family tree, DNA range bars, source reader with highlighted line spans, folders, handoff view and audit ledger.
- **Backend:** FastAPI and Pydantic. A deterministic pipeline turns claims into relationships, findings and leads. Lead statuses never depend on model output.
- **DNA check:** walks recorded parent links to the closest common ancestors and compares shared cM with a reference range for that relationship: 99% Ped-sim intervals for first to third cousins, approximate Shared cM Project ranges otherwise. It's a range-consistency check, **not a likelihood**.
- **Gemini (`gemini-3.5-flash`):** structured extraction, validated per item against strict Pydantic models, then a quote verifier. Every real response is recorded, so the demo replays it offline and re-verifies it, labelled "replay of a recorded response". We never fabricate a live AI result.
- **LangChain deepagents:** a restricted `create_deep_agent` harness with seven allow-listed tools wrapping KinFold's deterministic code: search and read records, test DNA hypotheses, verify claims, propose next steps, write a report. No filesystem, shell or URLs. Bounded calls and deadline, retries with backoff. Identity claims in its report are refused. Runs are recorded and replayed with every result recomputed.
- **Solana devnet:** the manifest digest goes into a Memo transaction. An anchor is stored only after the transaction is confirmed and its memo checked on-chain, and **Verify** re-checks it at any time.
- **MongoDB Atlas:** case storage, verified on a real cluster, with local JSON as the default.
- **Safety:** uploaded documents are untrusted evidence, never instructions (tests cover prompt injection). Synthetic or public data only.

## Challenges
- **Live Gemini rejected our schemas, twice.** First it gave a 400 on strict Pydantic schemas (`$ref`, `additionalProperties`, nullable `anyOf`). Then, after we sent size limits, it gave a 400 on `minItems`/`maxItems`. Each time we fixed what we *send* and kept validation strict on our side: we now validate each AI observation individually, so one bad item no longer discards the good ones.
- **A Windows line-ending bug hid our whole AI step.** Git on Windows checked the demo records out with CRLF, their hashes no longer matched the recorded Gemini responses, and the new lead silently never appeared. We found it during a live anchor on a teammate's laptop, then fixed it by normalising uploads and adding a regression test.
- **Deciding what counts as "supported".** A quote can be located exactly and still not support the claim. Our verifier prefers dropping a true claim to accepting an unsupported one, and it shows every rejection.
- **Honest on-chain status.** The UI says "anchored" only for a confirmed devnet transaction of the *current* digest, so after any change it goes back to "not anchored". We anchored three real states.

## Accomplishments
- The DNA check overturns the obvious story, and verified AI reading finds the branch that fits, with every step citing the exact lines it relies on.
- AI is accountable by construction: Gemini and the agent propose, KinFold verifies, and rejections stay visible.
- Real live runs of every integration (Gemini, deepagents, MongoDB Atlas, three Solana devnet anchors), recorded in `docs/VALIDATION.md`, and the whole demo still runs offline without keys.

## What we tested
- `pytest backend/tests research/genetics/tests`: **101 passed**. `npm run build`, `npm run test:anchor` (4) and `npm run test:package` (3) pass.
- `scripts/evaluate.py`: two held-out synthetic families with 6 candidate decisions. The full engine got 6/6 against 4/6 for a birth-range-only baseline. That's a small correctness check, not scientific validation.
- `npm run test:integration` against the real HTTP API: locates every citation, checks digests across Python and JavaScript, and confirms that an old digest stops matching after new evidence.

## What we learned
Evidence integrity isn't evidence truth. A shared-cM value fits several relationships, and a perfectly located quote can still be misread. The most useful thing a tool like this can do is show its work, keep its doubts visible, and leave the decision to a person.

## What's next
- **Paper to proof:** photograph a physical record, transcribe it line by line, and cite back to the photo (in progress).
- **Name linking** across records ("Patricia Hale" and "the former Patricia Novak") without guessing.
- **Real sign-in and signed audit entries**, so the handoff trail is attributable, not self-declared.
- **Validation:** relationship inference on simulated pedigrees with whole-family holdouts and declared baselines (`research/genetics/`).

## Built with
Tags: `react`, `typescript`, `vite`, `python`, `fastapi`, `pydantic`, `google-gemini`, `langchain`, `deepagents`, `mongodb-atlas`, `solana`, `node.js`.

- **MongoDB Atlas:** case storage. Verified on a real Atlas cluster; the case survives a full app restart with an identical evidence digest.
- **Solana devnet:** the lead timeline. Verified anchor of the Hale state (Lena Hale possible): https://explorer.solana.com/tx/4qWrFgPTGC8wxif392icaBQM7ijpqc289k48GWndCpMFhM4q4k3yZ5MfAwEoVBrE9qeMuN3q9BCHbTj48jRWpwFV?cluster=devnet

## Prize tracks
- **Arlequin, AI-Driven Forensics** (the sponsor confirmed the project fits, #4): AI applied to forensic genetic genealogy with accountability built in. DNA range checks on a recorded pedigree, word-for-word quote verification of every AI claim, an agent that can't change outcomes, a case handoff trail, and tamper-evident anchors of each research state. Synthetic data only; it identifies no one.
- **Best Use of Gemini AI:** Gemini reads messy historical records into typed claims, and every claim must survive a word-for-word quote check before it counts. Real `gemini-3.5-flash` runs are recorded and replayed with re-verification. Live annotations are also verified.
- **MongoDB Atlas:** cases persist in Atlas, verified with a real cluster. This is storage only, so describe it plainly.
- **Solana:** "Every lead gets a tamper-evident timeline". A judge or defence attorney can later check what was known, when, and what the AI actually said, without trusting the lab. These are real devnet Memo anchors, verified on-chain from the app (Explorer link above). An anchor proves the state existed unchanged; it doesn't prove the records are true.
- **LangChain "Best use of deepagents":** the agent does an investigator's job. It decides what to read and which relationship hypotheses to test against the DNA, then proposes next steps. It holds only allow-listed tools over deterministic code and can't change outcomes. A live `gemini-3.5-flash` run is recorded in `data/agent_runs/` and replays with every result recomputed.
- **Amazon "Best Practical AI":** the agent reasons, plans and takes multi-step actions. Its tools are bounded, every step is in a cited audit trail, and it has no ability to change outcomes.

## Demo video
**[DECIDE: link from #5]** Not recorded yet.

## Accuracy notes (keep in the submission)
- All people, records and DNA matches are synthetic. KinFold identifies no one.
- Lena Hale is a research lead, not an identification. DNA consistency is a range check on a recorded pedigree, not a likelihood. Evidence scores are heuristic, not probabilities.
- The AI step in the demo is a replay of a real recorded Gemini response, labelled as such in the UI.
- On-chain status is shown only for a confirmed Solana devnet transaction of the current evidence digest; otherwise the screen says "not anchored". An anchor proves a state existed unchanged, not that the records are true.
- The agent step in the demo is a replay of a real recorded agent run, with every result recomputed, and it's labelled as such.
- This is a hackathon research prototype, not a validated forensic system.
