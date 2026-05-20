# Vedix — Marketing Brief

**Date:** 2026-05-20
**Owner:** founder (single-operator at v3.0 launch)
**Status:** Standalone marketing-analysis track. Independent of the v3.0 engineering spec (`docs/specs/2026-04-30-v3-major-release-spec.md`). Hand this brief to a marketing analyst to run a full positioning, channel, and pricing analysis.
**Read in conjunction with:** `docs/specs/2026-04-30-v3-commercial-rebrand-and-monetization.md` (naming + payment infrastructure rationale).

---

## 0. One-page executive summary

**Product.** Vedix (working name; `vedix.ai`) is a research workbench that turns a topic into a submission-ready manuscript by orchestrating literature search, hypothesis design, experiment execution, claim auditing, and venue-specific typesetting end-to-end. It runs inside the user's existing AI coding assistant (Claude Code, Codex, Gemini) plus an optional hosted SaaS for non-CLI users.

**Core problem.** Scholarly writing has fractured across a dozen single-purpose AI tools — chat assistants, reference managers, literature search engines, statistical helpers, plagiarism detectors, journal templates. None of them owns the full chain from idea to submission, and none of them pre-empts the failure modes that *cause* a paper to be desk-rejected or retracted: fabricated citations, decorative references, claim-figure mismatches, p-hacking, ad-hoc methodology, AI-stylistic tells. A researcher today does the integration work by hand, in their head, and pays for that integration with time and reputation.

**The Vedix wager.** A single orchestrated pipeline — with seven structurally novel rigor mechanisms baked into the path from topic to submission — is more valuable to a working researcher than any individual best-in-class point tool, *because rigor compounds and the failure modes interlock*. We don't compete with ChatGPT or Overleaf or Zotero; we replace the human integration layer that sits between them.

**Attitude.** Vedix is a workbench, not a chatbot. The brand voice is scholarly, terse, evidence-anchored, and pointedly anti-AI-slop. We invert the dominant industry posture (which is "AI will write your paper for you") to "AI will keep you honest, then help you write." That inversion is the entire brand.

**Customer.** A working researcher — late-stage PhD, postdoc, or assistant professor — who is mid-paper, behind on a submission deadline, and quietly worried that the AI-assisted draft sitting in their Overleaf will not survive peer review. They are credentialed enough to recognize methodological failures when surfaced and frustrated enough to pay 1,290 ₽ / $14 a month to have those failures surfaced before a reviewer finds them.

**The wedge.** A single command — `/vedix <topic>` — that turns the existing AI-coding-assistant they already have open into the full pipeline. Free tier, BYOK, open-source, MIT-licensed. The conversion to Pro happens after the first run produces a manuscript that survives their advisor's review more cleanly than their last solo draft did.

**The moat.** (1) Seven clean-room rigor mechanisms that nothing else has wired together (see §4 of engineering spec). (2) First-class Russian-language support including ГОСТ-7.0.5 citation style — no major Western competitor serves the Russian academic market natively. (3) A trained per-discipline linguistic register classifier maintained centrally and re-trained quarterly. (4) Cross-host parity (Claude / Codex / Gemini) which structurally hedges against any single vendor's pricing or capability changes.

**12-month North Star.** 1,000 paying Solo subscribers and 50 Lab subscribers globally; ~3M ₽/mo ARR; one citation in a peer-reviewed methods paper authored by an external lab using Vedix.

---

## 1. The core problem (the brief from the field)

### 1.1 What's actually broken

Scholarly publishing has acquired three new pathologies in the AI era, on top of the older ones that never went away:

1. **Citation collapse.** Estimated 8–20% of references in AI-assisted drafts are fabricated (hallucinated DOIs, wrong authors, non-existent journals, plausible-but-fictional titles). The retraction rate for AI-assisted papers in 2024–25 has risen sharply in low-tier and predatory venues, and is starting to show up in mid-tier ones. Reviewers and editors have begun routinely checking 5–10 random citations per submission.

2. **Claim drift.** Sentences in the manuscript no longer correspond to numbers in the results. AI-rewritten paragraphs invert effect signs, round confidence intervals out of significance, or generalize a within-sample finding to "this demonstrates X in general." The author often does not notice because the revised sentence reads well.

3. **Stylistic flagging.** Reviewers, editors, and a growing population of "AI-tell" detectors (GPTZero, Originality.ai, Turnitin AI detection) now flag manuscripts that read as AI-generated. The flags trigger desk-reject regardless of underlying quality. Researchers want their drafts to read as written by a competent human peer, in their own discipline's register.

Stacked on top of these new pathologies are the older problems that AI is not solving:

- **Methodology drift.** The author chooses the test *after* seeing the data; reports R² without confidence intervals; reports p-values without effect sizes; omits failed control conditions.
- **Decorative citations.** References that exist but do not support the claim they're attached to. A reviewer who spot-checks one finds the trick and rejects.
- **Reproducibility theatre.** "Code available upon request" + a private GitHub URL that 404s within a year of publication. Or a Methods section that omits enough setup that another lab cannot replicate.
- **Venue-format friction.** The same paper has to be reformatted three times across three submission attempts to Elsevier / Springer / Frontiers, each with different reference styles, section orderings, and word limits.
- **First-language friction (acute for Russian researchers).** A non-native English speaker writes a methodologically strong paper, runs it through ChatGPT for language polish, and gets back a draft that reads as AI-generated, missing their discipline's register, and gets stylistically flagged. They had to choose between sounding like themselves and sounding like a competent peer.

### 1.2 Why now

Three converging forces make 2026 the right window:

- **Editorial fatigue.** Journals are openly publishing AI-disclosure policies (Nature, Cell, Lancet, IEEE all published explicit policies in 2024–25). Authors need a tool that *produces* the disclosure document automatically and can demonstrate, on demand, where every claim, citation, and figure came from.
- **The "AI tax."** Researchers pay $20–$60/mo for ChatGPT Plus + Cursor + Claude + Grammarly + Overleaf + Zotero. They are saturated, mildly cynical about new AI subs, but the actual integration work they do across these tools is still manual. A single tool that *replaces the integration* (not adds another point tool) is the only product they're still in market for.
- **Cross-host CLI maturity.** Claude Code, Codex CLI, and Gemini CLI all shipped multi-agent dispatch in late 2025. The plugin shell is now stable enough to ship a full research orchestrator as a free wedge into a paid SaaS upgrade — distribution that wasn't possible six months ago.

### 1.3 Why this specific problem set

We are not solving "AI cannot write." It can. We are solving the consequence of AI being able to write: that the bottleneck moved from prose generation to *rigor at scale*. Every research workflow now produces enough draft material that the cost of vetting it has become the binding constraint. Vedix sells time-to-trustworthy-draft.

---

## 2. The idea

### 2.1 In one sentence

> Vedix is a single-command research workbench that turns a topic into a venue-ready manuscript by running literature search, hypothesis design, experiment execution, claim auditing, and publisher-specific typesetting as one orchestrated pipeline — with seven rigor mechanisms baked into the path so the output is honest before it is polished.

### 2.2 In 100 words

Vedix lives inside the AI coding assistant a researcher already has open (Claude Code, Codex, or Gemini CLI). One slash command — `/vedix <topic>` — and the pipeline searches the literature, drafts a falsifiable hypothesis, designs and runs an experiment, audits its own claims against the resulting numbers, replays a pre-registration check, scores the citation graph for diversity and load-bearing-ness, and emits a manuscript in the user's chosen venue's format (Nature, Elsevier, Springer, Frontiers, ГОСТ — fourteen venues at launch). Free tier is open-source and BYOK; the Pro SaaS adds a trained linguistic register classifier, hosted job queue, and team-shared memory.

### 2.3 The product surface

| Layer | Free | Pro | Why |
|---|---|---|---|
| CLI plugin | ✓ MIT-licensed | ✓ | Distribution wedge. Researchers will install free and open. |
| Cross-host (Claude / Codex / Gemini) | ✓ | ✓ | Hedges against single-vendor risk. |
| All 7 rigor tracks | ✓ | ✓ | The moat is the *integration*, not the components. |
| Local register classifier (retrieval-grounded, Layer A) | ✓ | ✓ | Free users get real linguistic quality. |
| Trained register classifier (Layer B, fine-tuned) | trains locally on user's CPU/GPU | pre-trained models served | Pro saves the user 4–8 hours of one-time training. |
| Publisher templates | 3 bundled + 11 fetch-on-first-use | all 14 + premium-maintained | Free covers preprint + most submission paths. |
| Hosted job queue | ✗ | ✓ | Lets users without local compute run jobs. |
| Team-shared memory | ✗ | ✓ Lab tier | Multi-author collaboration. |
| Audit-log retention | 7 days | 90 days | Useful for institutional review. |

---

## 3. The attitude

This is the brand voice. Marketing copy, public posts, error messages, the README, the website, the speaker notes — all of these have to sound like a single voice.

### 3.1 Posture (what we are)

1. **Scholarly.** The product is a workbench for working researchers. Not for "creators." Not for "founders." Not for "growth marketers." We use the discipline's vocabulary, cite our sources, and assume the reader has a methodology background.
2. **Terse.** Pages are short. Sentences are direct. We avoid superlatives and hedges. We do not pad with "powerful," "revolutionary," "next-generation."
3. **Evidence-anchored.** Every claim on the marketing site links to a methods paper, a benchmark, a worked example, or a peer-reviewed source. The brand earns trust by writing the way our customers wish more papers would.
4. **Quietly confident.** No exclamation marks. No emojis. No "🚀 Let's go!" The product is the case.

### 3.2 Inversion (what we refuse)

The dominant AI-product posture in 2024–26 is **"AI will write your paper for you."** Vedix inverts this:

> **AI will keep you honest, then help you write.**

This single inversion is the entire brand. Every piece of marketing has to encode it. The pipeline is built to surface mistakes before publishing them, not to suppress mistakes for the appearance of polish. Customers buy us *because* we will tell them their citation graph is too self-referential and their hypothesis was post-hoc — not despite it.

### 3.3 Things Vedix will not do (the "no-go" list, public)

- We will not call ourselves an "AI scientist," "AI co-author," or "AI peer reviewer." The product augments the human researcher; the human is the scientist.
- We will not market a "paper generator." That framing belongs to the predators.
- We will not show stock-image researchers in white coats holding glowing tablets. We will use real screenshots and real manuscripts.
- We will not use the word "revolutionary." Or "powerful." Or "seamless."
- We will not promise blind acceptance rates or "passes detection" framing. Both are dishonest claims.
- We will not lock the core pipeline behind paid tiers. The integration moat lives or dies in open source.
- We will not silently inject AI-disclosure-evasion features. The provenance ledger is by design *honest disclosure*, not laundering.

### 3.4 Voice samples

Bad copy (don't write this):

> 🚀 Vedix is the world's first AI research scientist that revolutionizes how you write papers. With seamless integration and powerful agents, generate publication-ready manuscripts in minutes!

Good copy (write this):

> Vedix runs the literature search, drafts a falsifiable hypothesis, executes the experiment, and audits its own claims against the results — then formats the manuscript for your target venue. Open source. Bring your own API key. No template lock-in.

The second is calmer, denser, factual, and lands.

---

## 4. The customer

### 4.1 Primary ICP — "The Mid-Career Writing Researcher"

- **Role:** Late-stage PhD candidate (year 4+), postdoc, or assistant professor (tenure-track, pre-tenure).
- **Discipline:** STEM-leaning — computer science, biomedicine, chemistry, physics, applied math, geosciences. Lighter weight in humanities at launch; we add humanities support in v3.1.
- **Geography:** ~40% English-language primary (US, UK, EU, ANZ, India). ~25% Russian-language primary (Russia, CIS, Israel ex-USSR diaspora). ~35% bilingual researchers in EU non-Anglophone (Germany, France, Netherlands, Spain, Italy) and East Asia (Japan, South Korea, China — though China is GFW-constrained and not a primary target at launch).
- **Tooling.** Already uses Overleaf, Zotero, ChatGPT Plus or Claude Pro, sometimes Cursor or Copilot for code. Pays $40–$80/mo for tools out of personal funds or a small grant line. Familiar with the command line.
- **Pain.** Has 2–4 active manuscripts. Last paper took 6 weeks to format across two submissions. Has been "called out" at least once by an advisor or reviewer for an AI-stylistic tell. Has had at least one citation challenged in review.
- **Buying authority.** Their own credit card up to ~$30/mo or ~2,000 ₽/mo without internal-budget approval. Above that requires PI/grant approval.

### 4.2 Secondary ICP — "The Russian Domestic Researcher"

- **Role:** Same as primary, but operating in Russian academic system (ВАК-perechen journals, ГОСТ formatting, RSCI / РИНЦ citation databases).
- **Specific pains:**
  - Cannot use Stripe, paid global SaaS often unreachable
  - First-language draft has to be co-translated to English for international venues; current AI tools produce stylistically flagged English
  - ГОСТ-7.0.5 citation style is not supported by Zotero or Mendeley natively — has to be hand-formatted
  - Sanctions block access to some Western literature databases — needs Anna's Archive + arXiv + bioRxiv as primary sources
- **Why Vedix wins here:** No competitor serves this market natively. Vedix has ГОСТ output, ЮKassa payment, Russian register classifier, and Anna's Archive integration in the core product, not as an afterthought.
- **Size estimate:** ~150K active researchers in Russia (RSCI/РИНЦ-indexed). Of those, ~30K are STEM-active and bilingual. Of those, ~3K are early-adopter / tool-friendly. Of those, ~10% conversion to paid at launch year = ~300 paying Russian users — viable starter market.

### 4.3 Tertiary ICP — "The Lab Director"

- **Role:** PI of a small/medium lab (3–10 researchers). Pays from grant funds.
- **Pain:** Inconsistent rigor across lab members' drafts. Has to read every manuscript before submission and finds the same failure modes every time (citation collapse, claim drift, decorative references). Wants to push the rigor checks upstream so they see fewer broken drafts.
- **Why they pay:** Lab tier (4,900 ₽ / $49) for 5 users + shared MemPalace + 200 hosted jobs. They expense it via grant infrastructure. Average lifetime is 3–4 years (a grant cycle).
- **This is the highest-ARPU segment.** A handful of lab subscriptions is a meaningful revenue floor.

### 4.4 Negative ICP — who we explicitly don't serve

- **Undergrad coursework.** Vedix is not a homework-help tool. The pipeline cost (literature search, multi-agent dispatch) is not appropriate for an essay.
- **Predatory-journal authors.** We will not optimize for venues on Beall's List or known paper mills. The disclosure ledger surfaces venue reputation when it's known.
- **Reviewers using AI to write reviews.** That's the other side of the integrity collapse and not our market.
- **Non-academic content marketers.** "AI for SEO content" is a different product. We will not bend the positioning toward it.

### 4.5 Day-in-the-life sketch (primary ICP)

> Tuesday morning. The researcher (postdoc, biomedical, year 2 of a 3-year contract) opens her laptop. She has a Nature Communications resubmission due Friday — reviewers asked for a specific control experiment and a tighter introduction. She also has a new collaboration paper at draft stage for Elsevier's *Cell Reports Medicine*.
>
> She opens Claude Code in her project folder. She types: `/vedix add control experiment for the reviewer's comment` — Vedix re-runs the experiment script with the new control, regenerates the results figure, audits the new claims, and updates the Methods section in place.
>
> She then types: `/vedix switch venue cell-reports-medicine` — Vedix re-typesets the existing manuscript from Nature Communications format to Cell Reports format, updates the reference style, regenerates the cover letter template, and surfaces a `parity_report.json` showing nothing was lost in translation.
>
> Total elapsed time: 90 minutes for both. Last month, doing the same work by hand, took her two and a half days. She is sold for another month.

That story is the customer journey. Marketing has to make it feel that close to the ICP's actual Tuesday.

---

## 5. Jobs-to-be-done

Five JTBD statements, Christensen-style ("When ___, I want to ___, so I can ___").

1. **Citation integrity.** When I'm finalizing a manuscript that includes AI-assisted draft material, I want every reference verified against Crossref and DataCite before submission, so I don't have a reviewer find a fabricated DOI and reject the paper.

2. **Stylistic camouflage (legitimate).** When I'm a non-native English speaker writing for a Western venue, I want my draft to read in my discipline's native register without AI-stylistic tells, so reviewers and AI-detection tools don't flag the paper for the wrong reason.

3. **Venue switching.** When a paper is desk-rejected at venue A and I want to try venue B, I want the manuscript reformatted (template, reference style, section ordering, word limit) in a single command, so I don't lose two days to copy-paste.

4. **Pre-submission rigor pass.** When I've finished a draft and I'm one day from submission, I want the pipeline to surface every claim that isn't supported by an in-paper figure or table, every decorative citation, and every methodological gap, so I can fix them *before* a reviewer finds them.

5. **Reproducibility surfacing.** When a reviewer asks "is the code available?" I want a single artifact bundle — code + data hash + experiment script + provenance ledger — generated automatically, so I don't fail a reproducibility check on a paper that *is* reproducible.

Every marketing campaign should be tied to one specific JTBD. We avoid generic "make research easier" messaging because the customer doesn't believe that — they believe specific JTBD framings.

---

## 6. Value proposition

### 6.1 Lean canvas (Ash Maurya)

| Box | Content |
|---|---|
| **Problem** | (1) AI-assisted drafts get desk-rejected for citation collapse, claim drift, AI-stylistic flagging. (2) Venue switching costs 1–3 days of copy-paste. (3) Russian-language researchers have no native tool. |
| **Customer segment** | Late-PhD / postdoc / asst-prof STEM researchers; Russian-domestic researchers; small lab PIs. |
| **Unique value prop** | The only research pipeline that audits its own claims against figures, verifies every citation against Crossref, scores the citation graph for load-bearing-ness, and outputs in 14 venue formats — including ГОСТ — from a single command. |
| **Solution** | Cross-host CLI plugin + BYOK SaaS. Seven rigor mechanisms. Trained register classifier per discipline + language. |
| **Channels** | (1) Habr + vc.ru for Russia. (2) Hacker News + arXiv methods paper for global. (3) University seminars (HSE / MIPT / Skoltech, EMBL, MIT Media Lab). (4) Direct outreach to academic Twitter / Bluesky integrity communities. |
| **Revenue streams** | Solo 1,290 ₽ / $14 / mo; Lab 4,900 ₽ / $49 / mo; Institution from 24,900 ₽ / $249 / mo. BYOK so no token-cost passthrough. |
| **Cost structure** | (1) Infra: cloud job queue (~$200/mo at 1K users). (2) Vendor API for classifier training (~$300/mo at quarterly retrain). (3) Domain + ЮKassa + Stripe (~$50/mo). (4) Solo founder cost not counted at v3.0. |
| **Key metrics** | (1) Free-to-paid conversion %. (2) Lab-tier retention (gross monthly retention >95%). (3) Number of citing methods papers. (4) Time-to-first-submission for new Solo users. |
| **Unfair advantage** | (1) First-class Russian + ГОСТ — no Western competitor has it. (2) Cross-host parity hedges against vendor risk. (3) Seven rigor mechanisms wired together — the integration is the moat. |

### 6.2 Positioning statement

> For working STEM researchers who need to ship a manuscript that survives peer review, Vedix is a research workbench that runs literature search, hypothesis design, experimentation, claim auditing, and publisher-specific typesetting as one orchestrated pipeline — unlike chat assistants, reference managers, or single-purpose AI tools, Vedix audits its own work against the resulting figures and refuses to ship a draft with fabricated citations or unsupported claims.

This is the line that goes on the homepage, in the README h1, and on the first slide of every pitch.

---

## 7. Differentiation matrix

Customers will compare Vedix against several adjacent products. The brief for marketing analysts is: *do not pretend these alternatives don't exist, and do not pretend Vedix is "better at everything." Be specific about the seam.*

| Alternative | What it does well | Where Vedix wins | Where they win |
|---|---|---|---|
| **ChatGPT Plus / Claude Pro** | General conversational drafting, brainstorming | Pipeline orchestration, citation verification, venue-specific output, claim audit | Open-domain conversation, broad knowledge |
| **Overleaf** | LaTeX editor, real-time collaboration, template library | One-command venue switching, rigor mechanisms, end-to-end pipeline | Manual editing UX, browser-based collaboration |
| **Zotero / Mendeley** | Citation management, PDF library | Citation *verification* (Crossref / DataCite gate), counterfactual probing, graph analytics | Bibliography of 10K+ papers, browser-extension capture |
| **Sakana AI Scientist (the original)** | Autonomous research-paper generation in a sandbox | Cross-host CLI distribution, integration with existing tooling, BYOK, Russian-first, rigor mechanisms, real venue templates | Pre-built sandbox environments for specific ML tasks |
| **Scite.ai / Consensus** | AI-curated literature search with claim tagging | Pipeline integration (search is one step of many), counterfactual citation probing | Standalone literature-discovery UX |
| **Originality.ai / GPTZero** | AI-detection, plagiarism check | Producing drafts that don't trigger flags *because the rigor is real*, not because of camouflage | Detection-only |
| **Grammarly / DeepL Write** | Language polish, ESL support | Discipline-specific register matching, ГОСТ-style output | General-language polishing |
| **Imbad0202/academic-research-skills** (peer plugin) | Claude-Code-native rigor skills | Cross-host parity, Russian-first, publisher engine, hosted SaaS, seven independent rigor mechanisms (not borrowed) | Lighter footprint, no infrastructure |

**Marketing takeaway:** in every comparison, the answer is "use both, plus Vedix as the integration layer." We do not displace Zotero or Overleaf. We replace the *manual coordination work* between them.

---

## 8. Narrative & messaging

### 8.1 The core narrative (used in long-form posts)

> The promise of AI in research was that writing would get cheaper. It did. The problem is that the *cost of trusting a draft* didn't go down — it went up. Every reviewer now spends part of their review on AI-tell detection. Every editor now spot-checks citations. Every grad student knows someone whose paper was desk-rejected for a fabricated reference.
>
> The bottleneck moved. It used to be writing; now it's rigor at scale. Vedix is what we built when we realized the next useful AI tool wasn't another writer — it was an auditor that ran the writing too.

### 8.2 Tagline candidates (rank-ordered)

1. **"A research workbench, not a chatbot."** (Recommended. Encodes the inversion and the positioning in five words.)
2. **"Honest first, polished second."** (Encodes the attitude.)
3. **"Submission-ready, source-verified."** (More functional, less emotional.)
4. **"The pipeline from topic to typeset."** (Most descriptive; weakest on attitude.)
5. **"Research without the AI-slop tax."** (Punchy but risks sounding defensive.)

### 8.3 Three-line elevator pitch

> Vedix is a research workbench that turns a topic into a venue-ready manuscript by running literature search, hypothesis design, experimentation, claim auditing, and publisher-specific typesetting as a single orchestrated pipeline. It runs inside the AI coding assistant the researcher already has open, with first-class Russian and ГОСТ-style output. Open source. Bring your own API key. Pro adds hosted infrastructure and a trained linguistic classifier per discipline.

### 8.4 Hero messages by venue

- **Habr (RU technical audience).** Lead with the architecture: cross-host CLI parity, seven rigor mechanisms, ГОСТ output. Speak to the engineer.
- **vc.ru (RU startup audience).** Lead with the market: 150K Russian researchers, no native tool, sanctions-resistant payment, ИП-USN-6% legal entity. Speak to the founder-watcher.
- **Hacker News (global engineering audience).** Lead with the open-source claim, the BYOK model, and the seven clean-room mechanisms. Speak to the principled hacker.
- **arXiv methods paper (global research audience).** Lead with the rigor mechanisms as a methodological contribution. Cite Liang 2024 (AI-stylistic tells) and the 2025 retraction-rate papers. Speak to the peer.
- **Twitter / Bluesky (integrity community).** Lead with the citation-graph and counterfactual-probing demos. Show a real fabricated citation getting caught. Speak to the angry reviewer.
- **University seminars.** Lead with a 20-minute live walkthrough of one of the team's actual papers being run end-to-end. Speak to the curious graduate student.

---

## 9. Distribution + funnel hypothesis

### 9.1 Funnel stages

| Stage | Goal | Channel candidates | Conversion target |
|---|---|---|---|
| **Awareness** | "I've heard of Vedix" | Habr post, HN front page, arXiv methods paper, academic Twitter, conference workshop attendance | 50K impressions in M1; 250K by M6 |
| **Consideration** | "I'm looking at the README" | GitHub star, vedix.ai landing page, YouTube walkthrough, blog comparison posts | 5% of impressions → 12.5K visitors by M6 |
| **Trial** | Installed the plugin, ran first job | Single-command bootstrap (already shipped at v2.1.2), interactive host picker, frictionless free tier | 8% of visitors → 1K plugin installs by M6 |
| **Activation** | Completed a full pipeline run (manuscript generated) | Form-driven setup, sensible defaults per discipline, working examples preloaded | 50% of installs → 500 activated users by M6 |
| **Conversion (Solo)** | Subscribed to paid Solo tier | After 2nd or 3rd successful job, upsell prompt: "trained classifier + hosted queue" | 15% of activated → 75 Solo by M6 |
| **Conversion (Lab)** | Subscribed to Lab tier | After 1 Solo user invites 2+ teammates | 10% of Solo cohort converts to a Lab subscription within 3 months |
| **Retention** | Still paying month-over-month | Monthly newsletter, classifier-update changelog, new-venue announcements | 92%+ gross monthly retention at 12 months |
| **Referral** | Customer told a peer | In-product referral discount; methods paper citation; conference talk attribution | 0.3 net new free-tier users per paying user per month |

### 9.2 Channel ranking (priority for first 90 days post-launch)

| Rank | Channel | Why | First-90-day target |
|---|---|---|---|
| 1 | **Habr.com long-form post** (RU) | High signal in Russian academic + dev community; product is unique in this market | One post → 50K reads → 500 installs |
| 2 | **Hacker News Show HN** | Highest-signal first-impression for open-source / dev tools globally | Front-page → 200K impressions → 1K installs (and high-quality early users) |
| 3 | **arXiv methods paper** | Establishes peer credibility; cited going forward; lifetime value of one citation > 50 paid signups | One paper out by M3 |
| 4 | **University seminar tour** (HSE / MIPT / Skoltech, then EMBL / Crick / MIT Media Lab) | Best conversion-per-impression; in-room demos convert at 20–40% | 6 seminars by M6 → 200 installs |
| 5 | **YouTube walkthrough series** (EN + RU) | Long-tail organic discovery via search; SEO compounding | Weekly cadence; 12 videos by M3 |
| 6 | **vc.ru startup post** (RU) | Reaches RU founder + tech-press community; secondary to Habr | One post at launch |
| 7 | **Telegram channels** (`@nplusonemag`, etc.) | Direct distribution to Russian science community | Coordinated post wave at launch + monthly thereafter |
| 8 | **Conference workshops** (NeurIPS-RU, AINL, AIST) | High signal but slow cadence | 2 workshops in year 1 |
| 9 | **Academic-Twitter / Bluesky** (#AcademicTwitter / #AcademicSky) | Niche but high-conviction integrity community | Daily engagement; "found a fabricated citation" demo posts |
| 10 | **Cold email to lab PIs** | Highest CAC; only useful for Lab + Institution tier | 10–20 PIs per month |

### 9.3 Channels we explicitly will not use at launch

- **Google Ads.** CAC too high vs LTV for academic users at our price point.
- **Facebook / Instagram / TikTok.** Wrong audience.
- **Influencer partnerships.** No academic-science influencer reaches the buying segment efficiently.
- **Sponsored journal advertising.** Conflict-of-interest perception kills brand neutrality.
- **Affiliate / referral bounty schemes.** Risks pushing predatory-journal-author segments toward us. Honest referral discount only.

---

## 10. Pricing rationale

### 10.1 Anchors

| Comparable | Monthly RUB | Monthly USD | Notes |
|---|---|---|---|
| GitHub Copilot | 1,000 ₽ | $10 | Single-purpose code assist |
| ChatGPT Plus | 2,490 ₽ | $20 | General-purpose assistant |
| Cursor Pro | 1,950 ₽ | $20 | Code-context AI editor |
| Notion AI | 800 ₽ | $8 | Bolt-on to existing Notion |
| **Vedix Solo (proposed)** | **1,290 ₽** | **$14** | Research-specialized pipeline |
| **Vedix Lab (proposed)** | **4,900 ₽** | **$49** | 5-user lab tier |
| Scite.ai | ~1,500 ₽ | $20 | Citation-tagging point tool |

### 10.2 Why 1,290 ₽

- Slightly above Copilot (1,000 ₽) — signals "specialized for research"
- Below ChatGPT Plus (2,490 ₽) — fits in the "second AI sub" budget rather than competing for the primary AI sub
- Just under the psychologically anchored "1,500 ₽ academic tool" ceiling
- USD anchor at $14 — clean number, below Cursor / ChatGPT Plus, no token-cost confusion (BYOK)

### 10.3 Pricing sensitivity test (M3–M6)

- **A/B at launch:** half of new Solo signups see 1,290 ₽, half see 990 ₽. Compare 30-day retention and 90-day retention. If 990 ₽ has > 1.3x net revenue per cohort at 90 days, lower the price permanently.
- **Lab tier:** test 4,900 ₽ vs 6,900 ₽ in M3–M6. Lab buyers are less price-sensitive (grant-funded).

### 10.4 Discount structure

- **Annual prepay:** 2 months free (16.7% discount). Standard SaaS pattern.
- **Academic discount:** none. The price is already academic-segment-appropriate; introducing a "student discount" creates verification overhead and gives away ARPU on our core ICP.
- **Refund policy:** 14-day no-questions-asked. Surfaces obvious mismatches early.
- **Founder discount:** 50% off Lab tier for first 50 labs that subscribe (12-month grandfathered). Generates testimonials + early reference customers.

---

## 11. Risks + mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Anthropic / OpenAI / Google deprecate the CLI plugin / agent API we depend on | Medium | High | Cross-host parity (3 vendors) hedges this; new vendors added as they ship |
| 2 | A free open-source competitor ships first with the same integration moat | Medium | Medium | Move faster on the publisher-engine + Russian-language; those have longer integration tails |
| 3 | Russia payment infrastructure tightens further (ЮKassa restricted) | Low-Medium | High for RU revenue | Crypto fallback already designed; international USD revenue is the primary growth lane |
| 4 | An academic-integrity scandal involving an AI tool (not us) creates broad reputational drag on all AI-research products | High | Medium | The "rigor-first, honest-disclosure" positioning is the hedge — when others get caught, we look like the responsible alternative |
| 5 | The trained classifier overfits / underperforms in production | Medium | Medium | Layer A (retrieval-grounded) is a strong floor; classifier is an additive value, not a foundation |
| 6 | Russian-language market is too small to be standalone | Medium | Low | RU is a credibility wedge + a sanctions-hedged revenue floor, not a primary growth target |
| 7 | The brand name (Vedix) has an unresolved trademark conflict | Low-Medium | High if discovered late | Domain + USPTO + Rospatent sweep is a hard gate before any code references the name |
| 8 | A major journal explicitly bans the use of pipelines like Vedix | Medium | High | The provenance ledger + honest-disclosure design *is* the response; we predict the inverse — major journals will start requiring something like the ledger |
| 9 | Solo founder burnout / illness | Medium | Critical | Public roadmap, MIT license, recoverable infra. The product survives even if the company doesn't |
| 10 | Russian government regulation of foreign-API SaaS (LLMs) tightens | Low-Medium | High for RU customers | BYOK shields us — the customer owns the LLM relationship, not us |

---

## 12. KPIs (12-month measurement framework)

Tracking dashboard, monthly cadence. Each metric has a M3 / M6 / M12 target.

### 12.1 Funnel KPIs

| Metric | M3 | M6 | M12 |
|---|---|---|---|
| GitHub stars on `vedix/vedix` | 500 | 2,500 | 8,000 |
| Plugin installs (cumulative) | 300 | 1,500 | 6,000 |
| Activated users (≥1 full pipeline run) | 150 | 750 | 3,000 |
| Paid Solo subscribers | 25 | 150 | 1,000 |
| Paid Lab subscribers | 2 | 12 | 50 |
| Paid Institution contracts | 0 | 1 | 5 |
| MRR (RUB) | 35K ₽ | 250K ₽ | 1.8M ₽ |
| ARR (RUB) | 420K ₽ | 3M ₽ | ~22M ₽ |

### 12.2 Quality KPIs

| Metric | Target |
|---|---|
| Gross monthly retention | > 92% |
| Net Promoter Score (in-product survey, M2 onward) | > 40 |
| Time-to-first-activation (install → first manuscript) | < 45 minutes |
| Median pipeline runtime per job | < 30 minutes |
| Citation-verification false-positive rate | < 2% |
| Trained classifier F1 on holdout register-classification | > 0.85 |

### 12.3 Brand KPIs

| Metric | M12 target |
|---|---|
| Peer-reviewed methods papers citing Vedix (or its predecessor) | ≥ 3 |
| Conference talks given by external users (not us) | ≥ 2 |
| Habr cumulative reads on Vedix posts | ≥ 200K |
| HN appearances (M1 launch + organic resurfacing) | ≥ 3 |
| University seminars delivered | ≥ 6 |
| External contributors to the OSS repo | ≥ 15 |
| Mentions in Nature / Science / Lancet news sections | ≥ 1 |

---

## 13. Open marketing questions

Hand these to the marketing analyst — each is independently answerable.

1. **Tagline ratification.** Which of the 5 candidates in §8.2 lands best with the primary ICP? (Run a quick poll on academic Twitter / Bluesky / Habr.)
2. **Russian-vs-global lead market.** Do we lead the M1 launch in Russia (Habr → vc.ru) or globally (Hacker News → arXiv) or both simultaneously? Bilingual launch is operationally harder but doubles the impression base.
3. **Logo + visual identity scope.** Wordmark only (typography-driven, scholarly) vs wordmark + geometric mark? Budget for a designer at brand-launch time?
4. **Founder visibility.** Do we ship as a founder-led brand (Danil's face on the talks, GitHub profile prominent) or as a more anonymous "Vedix Labs" identity? Founder-led converts better for academic trust; anonymous gives optionality for later acquisition.
5. **Citing predecessor.** The plugin's origin story includes the Sakana AI-Scientist canonical code as a vendored dependency. Do we credit it explicitly in marketing copy (boosts academic credibility) or only in the technical README (cleaner brand positioning)?
6. **Russian academic-integrity organizations.** Should we proactively reach out to Диссернет, the РАН commission on falsification of scientific research, and the editorial boards of major ВАК journals to position Vedix as a tool *aligned with their goals*? Risk: politically charged in Russia. Reward: high credibility lift if it lands.
7. **Free-tier hosted-job allotment.** Zero hosted jobs (BYOK only) vs 2 free hosted jobs per month for new users (as a trial)? The two-job allotment likely lifts free-to-paid by 30–50% but adds infra cost per free user.
8. **Disclosure / methods paper authorship.** When we publish the methods paper on arXiv, do we list a single author (the founder) for credibility, or a multi-author including the AI agents transparently per the provenance-ledger philosophy? The latter is on-brand but novel and may attract distraction.
9. **Pricing currency display.** Default RUB display for `.ru` traffic, USD for elsewhere — or always dual-display? Dual increases conversion in non-RU markets (less mental conversion friction) at the cost of clutter.
10. **OSS contributor compensation.** External contributors get nothing (standard MIT), small bounties for first contribution ($25–$100), or grant a small ownership pool in the for-profit entity for top contributors? The third is unusual but on-brand for an academic-community product.

---

## 14. What this brief is *not*

This is a marketing-analysis brief, not a marketing plan. It defines:

- the problem we solve (§1)
- the idea (§2)
- the attitude (§3)
- the customer (§4)
- the jobs-to-be-done (§5)
- the value proposition (§6)
- the differentiation (§7)
- the narrative (§8)
- the funnel hypothesis (§9)
- the pricing rationale (§10)
- the risks (§11)
- the KPI framework (§12)
- the open questions (§13)

A marketing analyst hired to take this forward should produce:

- A test plan for each of the 10 open questions
- A 90-day go-to-market plan with specific dates and content briefs
- A media kit (logo files, screenshots, two-page brand-style guide)
- Three sample long-form posts (Habr, vc.ru, HN) ready to publish
- A pricing-test instrumentation plan (which events to log, which dashboards)
- A 12-month editorial calendar (YouTube + Habr + arXiv methods paper + university seminars)

Those artifacts are the analyst's deliverables — they sit *downstream* of this brief.

---

## 15. Document lifecycle

- **Owner:** the founder.
- **Cadence:** revisit at every minor release (v3.0.x) or at any pivot. Re-cut §4 (customer) and §9 (funnel) at M3 / M6 / M12 against actual data.
- **Cross-references:**
  - `docs/specs/2026-04-30-v3-major-release-spec.md` — engineering spec (the *what* of the product)
  - `docs/specs/2026-04-30-v3-commercial-rebrand-and-monetization.md` — naming + payment infrastructure
- **Sign-off block (fill at decision time):**
  - [ ] Founder approves brand attitude (§3)
  - [ ] Founder approves ICP definition (§4)
  - [ ] Founder approves pricing (§10)
  - [ ] Marketing analyst engaged (date, contact)
  - [ ] First Habr post live (date, URL)
  - [ ] First HN Show HN posted (date, URL)
  - [ ] arXiv methods paper preprint posted (date, arXiv ID)
