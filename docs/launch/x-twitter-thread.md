# X / Twitter launch thread (12 tweets)

> One tweet per line break. Each tweet stays under 280 characters; the spec
> for the v3.0 launch announcement.

---

**1/12**
I'm shipping Vedix v3.0 today — a cross-host research workbench that turns
a topic into a venue-ready manuscript.

Open source (MIT). BYOK. Runs in Claude Code, Codex CLI, or Gemini CLI.

The bet: rigor at scale matters more than prose generation.

https://github.com/vedix/vedix

---

**2/12**
Seven rigor mechanisms baked into the pipeline:

• Failure-mode learning
• Citation graph analytics
• Counterfactual citation probing
• Adversarial multi-pass review
• Semantic revision diff
• Pre-registration replay
• Provenance ledger + auto-disclosure

One thread per mechanism →

---

**3/12** Failure-mode learning

HDBSCAN over the pipeline's own historical failures. The largest clusters
become pre-flight checks for new jobs.

Top current cluster: "hypothesis depends on a variable the experiment
never measured." Now caught seconds before the experiment runs.

---

**4/12** Citation graph analytics

Three metrics on every reference list:
• Gini freshness (year concentration)
• Density per section
• Self-citation ratio

Out-of-band values surface in the rigor report automatically. No more
hunting them by hand.

---

**5/12** Counterfactual citation probing

For each citation: LLM judge swaps in a plausible decoy and asks if the
sentence's meaning changed. If no — the citation is decorative, not
load-bearing.

On my own drafts this flagged ~12% of "polite" citations I'd have left in.

---

**6/12** Adversarial multi-pass review

Same reviewer runs twice with opposing stances:
• Steelman — find the strongest reading
• Break — find the weakest point

Agreement = robustness signal.
Disagreement = fragile claim, flagged for revision.

---

**7/12** Semantic revision diff

Between revisions, embed every claim sentence. Report pairs whose cosine
dropped below threshold — claims whose meaning silently inverted while
the prose changed.

The most underrated failure mode in AI-assisted editing.

---

**8/12** Pre-registration replay

Before the experiment: commit prereg (hypothesis, primary metric,
expected direction, tolerance).
After the experiment: auditor replays prereg vs actual results.

Silent post-hoc adjustments get flagged. Honesty by construction.

---

**9/12** Provenance ledger + auto-disclosure

Every sentence in the final manuscript carries tags:
• Which agent wrote it
• Which model
• Which sources backed it

Auto-disclosure pass converts those tags into a journal-ready AI-
disclosure paragraph in your venue's language.

---

**10/12**
23 publisher templates bundled. 7 languages first-class (en/ru/es/de/fr/
zh/ja). 13 BYOK providers including the Chinese (DeepSeek, Qwen, Moonshot,
Zhipu) and Russian (GigaChat, YandexGPT) ones, plus self-hosted OpenAI-
compatible.

No paywall on features.

---

**11/12**
Vedix.ai SaaS launches with the same release.

Free tier: every feature included.
Paid tiers: buy only throughput / concurrency / storage.

Multi-region payments: Stripe, PayPal, YuKassa, SberPay, CloudPayments,
Boosty, crypto.

---

**12/12**
MIT licensed.

🔗 Source: https://github.com/vedix/vedix
🔗 Docs: https://docs.vedix.ai
🔗 SaaS: https://vedix.ai

If you've felt the gap between fluent AI prose and a manuscript that
survives review — try it and tell me what's still broken.
