# Two-minute local demo

**Before you start:**
- Run `npm start` and open http://127.0.0.1:5173. Reset the synthetic case from Research log.
- Keep two files ready to upload:
  - `data/examples/synthetic-hale-obituary.txt`
  - `data/examples/synthetic-hale-birth-announcement.txt`
- Say explicitly that all people and DNA matches are synthetic.

**Gemini setup:** AI extraction needs a recorded Gemini response, or a live key (see "Before the event" below). Without either, the uploads are kept and shown as "Reviewed without structured extraction", and no AI result is invented.

**0:00–0:20: The question.** "An unidentified person shares 220 cM of DNA with Ruth Mercer. The records point at three of Ruth's nieces. Kinfold checks whether that story holds up." Run the investigation.

**0:20–0:50: The DNA says no.**
- Open Candidate leads. All three recorded leads are excluded.
- Under the recorded pedigree, each would be Ruth's niece: about 1,201–2,282 cM expected, against 220 observed.
- Point out the record-based reasons too: June's birth year is outside the estimated range, Nora has an alive record after the death estimate, and Clara's birth sources conflict.
- The first next action reads "Search branches that fit 220 cM": first cousins once removed or second cousins, through Ruth's grandparents.

**0:50–1:30: AI reads messy records, and every claim must quote its source.**
- Upload the Hale obituary and the 1972 birth announcement, then investigate.
- Gemini proposes claims. Kinfold accepts a claim only if:
  - the quote is verbatim in the cited lines;
  - the quote names each person;
  - the quote states the year.
- Show the two rejected claims from the recorded `gemini-3.5-flash` run. Both are probably true, but the quotes the model chose don't state them outright, so the conservative verifier drops them. "We'd rather drop a true claim than accept an unsupported one."
  - George Hale "alive in 2008": implied by "survived by" in a 2008 obituary, but the quote never states the year.
  - A George–Patricia marriage: the record supports it ("Mr. and Mrs. George Hale … the former Patricia Novak"), but the quote has no explicit marriage wording.
- Because that link was dropped, the graph shows "Patricia Hale" and "Patricia Novak" as separate people. Say so in one sentence; it's the verifier being honest, not a bug.

**1:30–1:45: A new lead appears.**
- The obituary says Frances Hale was Arthur Mercer's sister. Lena Hale is Frances's granddaughter.
- Kinfold proposes Lena itself ("Found by Kinfold"): she was born in 1972, inside the estimated range, and the 220 cM DNA fits. Under the recorded pedigree she is Ruth's first cousin once removed (expected 102–980 cM).
- The model gave her birthplace only as "Cooper Hospital", so Kinfold does not award a region point it can't support.
- Open a citation to show the exact line behind each step.

**Optional, 10–15 s: the agent checks the lead.** This replays the recorded live `gemini-3.5-flash` run in `data/agent_runs/`.
- On Lena Hale's card, select **Investigate with the agent**. The panel shows what the deepagents investigator chose to check:
  - all 12 records read;
  - 7 DNA hypotheses tested: first cousin once removed fits 220 cM, first cousin and great-aunt don't;
  - 7 claims verified and 1 rejected (it used an ID in place of a name, then fixed it);
  - 3 next steps, including checking that Frances and Arthur were full siblings.
- "The agent chooses what to check; Kinfold's own code computes every answer. It can't change a lead, and it isn't allowed to claim an identity."
- With no key set, the panel says "Replay of a recorded agent run". Without a recording, the button explains that no agent is configured. Skip this beat in that case.

**1:45–1:55: Every lead gets a tamper-evident timeline.**
- Open **Evidence integrity**, then select **Anchor this state**. This needs `KINFOLD_SOLANA_KEYPAIR` (see the README). The timeline shows the new anchor: Lena Hale as a new lead and 2 records added, with an Explorer link.
- "A hash of the cited records, the AI's raw outputs and the lead decisions is now on Solana devnet. Anyone holding the research pack can check what was known, when, and what the AI actually said. It proves this state existed unchanged; it doesn't prove the records are true."
- Optional: add any record and reopen Evidence integrity. It reads "current evidence differs from anchor #N".
- Without a configured keypair, skip this beat. The screen correctly says "Not anchored on-chain".

**1:55–2:00: Honest boundaries.** "This is a research lead, not an identification. DNA consistency is a range check on a recorded pedigree, not a likelihood. On-chain status is shown only for a confirmed devnet transaction."

**Recorded run:** `data/ai_cache/` holds real `gemini-3.5-flash` responses for both Hale records, recorded on 2026-11-14. With no key set, the app replays them and labels them as a replay. With a key set, a failed live call (for example a 503 overload) falls back to the recording and says so. A successful live run never overwrites an existing recording. `gemini-3.8-flash` returned 503 overloads while we recorded. **Record the demo video with no key set**, so it shows exactly the run described here.

**To re-record:**
1. Put `KINFOLD_AI_MODE=gemini`, `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`.
2. Run the upload once. This records Gemini's raw response in `data/ai_cache/`.
3. Commit that cache so the demo replays the real recorded response offline. The finding then says "replay of a recorded response" with its timestamp.
4. If the live model makes different mistakes than the ones above, describe what it actually did.
