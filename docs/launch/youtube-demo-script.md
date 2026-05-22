# YouTube demo script — Vedix v3.0 (8 minutes)

**Working title:** Vedix v3.0 — one command, topic to venue-ready manuscript
**Target length:** 7:30 to 8:30
**Format:** Screencast + voiceover, 1080p, 30fps
**Capture:** OBS Studio, single source (main display)

---

## Pre-roll checklist

- Empty Claude Code session at 100% zoom on a single 16:9 monitor.
- Local Vedix install fresh; classifiers downloaded; no jobs in queue.
- Anthropic + OpenAI BYOK keys loaded into `~/.vedix/secrets.yaml`.
- Network up; one tab open to docs.vedix.ai for the closing CTA.
- Microphone tested at -12 dB peak.

---

## 00:00 &mdash; 00:30 &mdash; Cold open

> **Voiceover:**
> "Most AI tools can write you a paper. None of them will tell you
> the paper is honest. Here is what I built instead."

Screen: blank Claude Code prompt. Cursor blinking.

---

## 00:30 &mdash; 01:00 &mdash; Slash command + setup form

Type:

```text
/vedix
```

Setup form appears in the chat panel. Walk through it field by field:

- Topic: `Does adding dropout regularization improve test R^2 on a
  synthetic regression task?`
- Discipline: `computer_science`
- Language: `en`
- Venue: `preprint`
- Hypothesis style: `confirmatory`
- Experiment type: `computational`
- Primary metric: `r_squared`
- Expected direction: `increase`
- Tolerance: `0.05`

> **Voiceover:**
> "Nine fields. The same nine fields whether you're submitting to Nature
> or to a working paper repo."

Submit. Job ID prints.

---

## 01:00 &mdash; 02:30 &mdash; Literature phase

Pipeline starts. Progress stream shows phase=literature. Highlight:

- Live queries against Semantic Scholar, OpenAlex, arXiv.
- Full-text retrieval &mdash; not abstract scraping.
- Reference list grows in a side panel as papers are accepted into the
  corpus.

> **Voiceover:**
> "This is the actual literature. Vedix won't cite an abstract; it pulls
> the full text. If the full text isn't reachable, the paper doesn't
> make the reference list."

---

## 02:30 &mdash; 03:00 &mdash; Hypothesis + rationale + prereg

Cut to the hypothesis appearing. `rationale.md` companion document opens.

> **Voiceover:**
> "Before the experiment runs, the hypothesis gets pre-registered. After
> the experiment, the prereg replay catches silent post-hoc adjustments."

Show `preregistration.json` in the side panel.

---

## 03:00 &mdash; 03:45 &mdash; Experiment runs

Phase=experiment. Show the generated Python file scrolling, then the
`results.csv` appearing.

> **Voiceover:**
> "The same machine wrote the experiment code, ran it, and captured the
> results. The numerical claim auditor reads results.csv before any
> number is allowed into the prose."

---

## 03:45 &mdash; 04:30 &mdash; Numerical audit catches a mismatch

(Pre-arranged: I'll seed a deliberate mismatch &mdash; a 0.92 vs 0.91
disagreement &mdash; into the draft so the auditor catches it on camera.)

Auditor output prints; mismatch flagged with the exact line.

> **Voiceover:**
> "This is the rigor track in action. The manuscript said 0.92; the CSV
> says 0.91. The pipeline refuses to ship a number that the data doesn't
> back."

---

## 04:30 &mdash; 05:00 &mdash; Manuscript renders

Phase=typesetting. The manuscript PDF appears in `~/.vedix/jobs/<id>/`.

Open the PDF. Scroll the abstract and intro on screen.

> **Voiceover:**
> "Twenty-three publisher templates. The preprint default uses a generic
> Overleaf layout; for a Cell or IEEE submission, you change one flag."

---

## 05:00 &mdash; 05:30 &mdash; Counterfactual citation probe

Cut to the counterfactual probe output. One citation flagged as
decorative.

> **Voiceover:**
> "For every reference, the probe asks: if I replace this citation with
> a plausible decoy, does the sentence still mean the same thing? If
> yes, the citation isn't load-bearing. Here, two are."

Walk through the two flagged citations on screen.

---

## 05:30 &mdash; 06:00 &mdash; Adversarial review

Cut to the adversarial review pane. Show the steelman + break scores
side by side.

> **Voiceover:**
> "Same reviewer, two stances. Where they agree, the claim is robust.
> Where they disagree, the manuscript flags the claim for revision."

---

## 06:00 &mdash; 06:30 &mdash; Provenance ledger

Open the web UI in a browser tab. Hover over sentences in the
manuscript; tooltips show per-sentence provenance: agent, model,
sources.

> **Voiceover:**
> "Every sentence carries its own audit trail. Hover anywhere; the
> ledger tells you who wrote it and why."

---

## 06:30 &mdash; 07:00 &mdash; Retypeset to a journal

Back to the CLI:

```text
/vedix retypeset <job_id> --venue elsevier:cell-reports-medicine
```

Show the publisher engine reusing manuscript content and rebuilding the
LaTeX class wiring. 90 seconds on screen, cut to the new PDF.

> **Voiceover:**
> "Same content, new venue. The publisher engine doesn't re-run the
> experiment; it just re-typesets."

---

## 07:00 &mdash; 07:30 &mdash; Auto-disclosure + preprint submit

Open `ai_disclosure.md`. Show the journal-ready disclosure paragraph.

Then:

```text
/vedix submit-preprint <job_id> --server arxiv
```

(Dry-run if you're not actually pushing live during the demo.) Show the
returned preprint ID and arXiv URL.

> **Voiceover:**
> "The disclosure is auto-generated from the provenance ledger in the
> language of your venue. The preprint submitter takes the same job ID
> and posts it to arXiv, bioRxiv, OSF, SSRN, or any SWORD endpoint."

---

## 07:30 &mdash; 08:00 &mdash; Wrap + CTA

Switch to the docs.vedix.ai tab. Walk through the install command at the
top of the home page.

> **Voiceover:**
> "Vedix is MIT-licensed. Install on Claude Code, Codex CLI, or Gemini
> CLI in one line. The hosted version at vedix.ai has every feature on
> the free tier. Links in the description. Thanks for watching."

End card: GitHub URL + docs URL + vedix.ai URL.

---

## Post-production notes

- Cut every dead second; aim for sub-eight minutes total.
- Highlight key terminal regions with a subtle border (FFmpeg crop +
  border filter), not zoom-and-pan.
- Add captions for accessibility; the Russian translation lives at
  `docs/launch/youtube-demo-script-ru.md` (separate file, future block).
- Thumbnail: split-screen, left = blank Claude Code prompt, right =
  rendered manuscript first page; overlay "vedix v3.0" in Inter Black.
- Description copy: paste docs/launch/hn-show-hn.md content (English) +
  install one-liner + GitHub URL.
