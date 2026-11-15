# Paper to proof: photographed records (#26)

A lot of genealogy evidence is still paper: newspaper clippings, family Bibles, courthouse records photographed on a phone. Genealogists are taught to check every transcript against the original, because transcripts drop, misspell and invent words. Kinfold ties each verified claim back to the line of the photo it came from.

## Flow
1. **Capture** (`POST /api/cases/{id}/photos`): a webcam snapshot, a phone photo or a file. Only JPEG, PNG and WebP are accepted, up to 4 MB, and the type is checked against the file's actual bytes.
   - The SHA-256 of the original bytes is recorded on arrival.
   - The bytes are stored unchanged, keyed by that hash: `blobs/` in the JSON store, a `blobs` collection in MongoDB.
   - `GET …/photos/{photo}/image` refuses to serve bytes that no longer match the recorded hash.
2. **Transcribe** (`POST …/photos/{photo}/transcribe`): Gemini vision returns one entry per line with a `[ymin, xmin, ymax, xmax]` box (0–1000).
   - Unreadable words are written `[?]` and the line is flagged uncertain. Spelling is never corrected.
   - The reply is validated strictly: a box out of range or inverted makes the whole transcription invalid.
   - The image is untrusted evidence. The prompt tells the model to ignore any text in it that addresses it.
3. **Confirm** (`POST …/photos/{photo}/confirm`): a person checks each line against the photo.
   - There must be exactly one entry per transcribed line, so every line keeps its box. Edits are recorded as corrections.
   - The confirmed text becomes a `photo_transcription` record.
   - Its provenance holds the image hash, the line boxes, the transcription's model and source with its `raw_sha256`, the corrections, and an authenticity note: the text is a model transcription confirmed by a person, a derivative copy.
4. **Investigate:** the existing extraction and quote verification run on the confirmed text unchanged. A citation's `start_line..end_line` maps to `line_boxes[start-1..end-1]` on the photo.
5. **Anchor:** the record's provenance is part of the evidence manifest, so the photo hash and line boxes are sealed into the digest that a Solana anchor records. The manifest's shape didn't change, so earlier anchors still verify.

An unconfirmed photo is not evidence and is not in the manifest.

## Recordings and replay
- **Transcriptions** are recorded in `data/ai_cache/transcriptions/<sha256(prompt version, model, image sha256)>.json`.
  - A live run records once and never overwrites.
  - Without a live model, a recording replays only for the **exact same image bytes**. Re-photographing the clipping gives new bytes and so needs a live call.
  - With neither, the endpoint returns 409. It never fabricates a transcription.
- **Extraction** of the confirmed text is recorded and replayed by text hash, as for typed uploads.

**Recorded live run (`gemini-3.5-flash`, 2026-11-15 UTC):** on `data/examples/print/hale-birth-clipping.png`, the clipping rendered from the printable page:
- Gemini transcribed 13 lines, none uncertain, every one correct.
- Extraction proposed 2 claims from the confirmed text, and both passed verification.
- With the typed obituary, Lena Hale appears as a lead, cited to photo lines 4–7 and 6–7.

`test_committed_live_recordings_replay_the_printed_clipping_without_a_key` replays this offline.

## Demo documents (synthetic)
- **`data/examples/print/hale-birth-clipping.html`:** a printable clipping from the fictional *Camden Clarion*. It carries the same synthetic text as `synthetic-hale-birth-announcement.txt` and a visible "Synthetic record" footer.
  - To print: print at 100% scale and cut along the dashed line.
  - Opening it with `#clip` hides the instructions, for a clean screenshot.
  - The newspaper name is fictional on purpose; a real masthead on a fabricated clipping would be misleading.
- **`data/examples/print/hale-bible-handwritten.jpg`:** a synthetic family-Bible page handwritten by Reyansh and photographed on a phone, with "(Synethetic, kinfold demo)" written on it.
  - **Recorded live run (`gemini-3.5-flash`, 2026-11-15 04:24 UTC):** 6 lines, none flagged uncertain. Gemini copied the page **as written**, including the misspellings "couper Husipital" and "Synethetic".
  - After confirming as-is and investigating, extraction proposed 3 claims and verified all 3. Lena Hale appears, cited to photo lines 2–3 and 2–4.
  - A second live read of the same photo returned "Cooper Hospital, Camden, N.J.", silently correcting the spelling. Handwriting reads vary between runs, which is why a person confirms every line against the photo.
  - The committed recording is the first, as-written read. The no-key replay test is `test_committed_handwritten_page_replays_as_written_and_finds_lena`.
  - Replay with no key works only if the lines are confirmed unchanged. Editing a line changes the text, and the edited text then needs a live extraction.

## Limits
- This shows the case hasn't been altered since it was anchored. It doesn't show the paper is genuine or the transcription is right; the person who confirms each line is responsible for that.
- The boxes are the model's estimate of where each line is, not measured coordinates.
- One API worker. Images in MongoDB were tested only through the JSON store, not against Atlas.
