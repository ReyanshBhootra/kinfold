# Two-minute demo video

**The shape: who → why → how.** Judges skim about 200 projects, and most have never heard of genetic genealogy. Spend the first 40 seconds on who we are and **why this matters**, using one plain-English picture and one real story. Then show the product: no code, no terminal. Every quoted line is meant to be said out loud: about 300 words, which fits 2:00 at a brisk, natural pace (about 155 words a minute). **Time one read-through.** If it runs long, cut the agent beat (1:35) first.

## Before you record
- Pull the latest `main`, leave `GEMINI_API_KEY` **unset** (so the AI and agent steps replay the real recorded runs exactly), and keep `KINFOLD_SOLANA_KEYPAIR` set for the anchor beat. Run `npm start`, open http://127.0.0.1:5173, and zoom the browser to 110–125% so the text is readable in the video.
- Reset the synthetic case (Research log → Reset synthetic case). Have `data/examples/synthetic-hale-obituary.txt` and `synthetic-hale-birth-announcement.txt` ready.
- To save time on camera, do the uploads and the agent run **before recording** and cut straight to the result. The storyline at the top shows each step's state, so the jump is easy to follow.
- **Turn on captions** (YouTube auto-captions, then fix the names). Many judges watch without sound.
- Record the voice-over separately if you can, and keep each beat to one take.

## Script

### 0:00–0:10 · Who we are and what Kinfold is
**On screen:** the Kinfold title slide or the app's landing page.
> "Hi, we're Reyansh and Shippy. This is **Kinfold**: a research assistant that checks every family-tree lead against the DNA, and won't believe anything the AI says without a quote."

### 0:10–0:40 · Why it matters (the part judges remember)
**On screen:** a simple slide: *DNA match → distant cousin → family tree → one person*. Then a headline-style slide with the numbers below.
> "When police have DNA but no name, genetic genealogists look for the unknown person's **distant cousins** in public DNA databases. Then they build those cousins' family trees **backwards** until one person fits. That's how the Golden State Killer was caught in 2018, and more than a thousand cases since. The U.S. still has about **sixteen thousand** unidentified people."
>
> "But one weak link can point at the wrong person. An innocent filmmaker once became a murder suspect because his father's DNA nearly matched. Add AI writing confident family trees, and every link has to be checkable."

### 0:40–0:55 · The DNA says no
**On screen:** Candidate leads. Point at the storyline, then at Clara's red DNA bar.
> "In this fully synthetic case, someone shares 220 centimorgans of DNA with Ruth, and the records point at her three nieces. But a niece should share 1,200 to 2,300, so Kinfold rules all three out and shows why."

### 0:55–1:20 · AI reads messy records, but must quote them
**On screen:** the two "AI read" findings, then a rejected claim.
> "We add two new records. Gemini proposes claims, and Kinfold keeps one only if its quote is word for word in the record and names every person and year. These two were dropped: probably true, but the quote doesn't say it. We'd rather lose a true claim than trust an unsupported one."

### 1:20–1:35 · A new lead appears
**On screen:** Lena Hale's card, "Found by Kinfold", with the green DNA bar.
> "Those verified lines reveal a new branch, and Kinfold finds **Lena Hale** on its own: born in 1972, and as a first cousin once removed, 220 fits."

### 1:35–1:47 · An agent double-checks it
**On screen:** the agent panel. Point at the seven-hypothesis chart.
> "A LangChain deep agent then double-checks Lena. It reads the records and tests seven relationships against the DNA. Kinfold computes every result, and the agent can't change any lead."

### 1:47–1:55 · Tamper-evident timeline
**On screen:** Evidence integrity, then Anchor this state, then Verify. The Lead timeline shows "On-chain: transaction found".
> "Finally, we anchor a hash of this exact state on Solana, so anyone can later prove what was known, and when."

### 1:55–2:00 · Close
**On screen:** the storyline with all six steps checked.
> "Kinfold doesn't name anyone. It shows its work, so a human can decide."

## Say this, not that
- Say "**lead**", "**consistent with the DNA**", "**range check**". Never say "identified", "match confirmed" or a percentage.
- Say "**synthetic case**" once, clearly, at 0:40.
- If you drop a beat to save time, drop the agent (1:35) or the anchor (1:47), never the why.

## Real-world facts used above (sources)
- Golden State Killer, 2018: genetic genealogy led to Joseph DeAngelo's arrest; widely seen as the start of the technique. [Wikipedia: Investigative genetic genealogy](https://en.wikipedia.org/wiki/Investigative_genetic_genealogy)
- "More than a thousand cases": a public registry counted 1,130 publicly disclosed cases solved by the end of 2023. [Genealogy Explained, 2023 recap](https://www.genealogyexplained.com/blog/the-figg-blog-a-recap-of-2023-nine-years-of-figg/). An academic dataset counted 545 criminal cases by the end of 2022 ([Criminal Legal News](https://criminallegalnews.org/news/2023/aug/1/forensic-genetic-genealogy-has-solved-545-cases-and-counting)), so "more than a thousand" is the registry's broader count.
- "About sixteen thousand unidentified people": NamUs lists 15,946 active unidentified-person cases (May 2026). [NamUs monthly report](https://namus.nij.ojp.gov/sites/namus/files/media/document/namus-stats-all-may-2026.pdf)
- The innocent filmmaker: in the Angie Dodge case, police pursued a filmmaker after his father's genealogy-database DNA came close to the crime-scene profile. His own DNA cleared him. [PBS NewsHour](https://www.pbs.org/newshour/show/a-father-took-an-at-home-dna-test-his-son-was-falsely-accused-of-murder)

**Recorded run:** `data/ai_cache/` holds real `gemini-3.5-flash` responses for both Hale records, recorded on 2026-11-14. With no key set, the app replays them and labels them as a replay. With a key set, a failed live call (for example a 503 overload) falls back to the recording and says so. A successful live run never overwrites an existing recording. `gemini-3.8-flash` returned 503 overloads while we recorded. **Record the demo video with no key set**, so it shows exactly the run described here.

**To re-record:**
1. Put `KINFOLD_AI_MODE=gemini`, `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`.
2. Run the upload once. This records Gemini's raw response in `data/ai_cache/`.
3. Commit that cache so the demo replays the real recorded response offline. The finding then says "replay of a recorded response" with its timestamp.
4. If the live model makes different mistakes than the ones above, describe what it actually did.
