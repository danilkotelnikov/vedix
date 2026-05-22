# Show HN: Vedix — cross-host research workbench with seven rigor mechanisms (open-source)

I'm shipping Vedix v3.0 today &mdash; a research workbench that runs inside
Claude Code, Codex CLI, or Gemini CLI. One command turns a topic into a
venue-ready manuscript by running literature search, hypothesis design,
experimentation, claim auditing, and typesetting in 23 publisher formats.

The thesis: AI assistants are great at producing fluent prose and terrible
at the four things that matter for a real manuscript &mdash; making sure
the experiment ran what the hypothesis claimed, the numbers cited match
results.csv, the references exist and are load-bearing, and the prose
hasn't silently inverted between revisions. Vedix bakes seven rigor
mechanisms into the pipeline so the output is honest before it's polished.

The seven mechanisms:

1. **Failure-mode learning** &mdash; HDBSCAN over the pipeline's own
   failure history turns recurring failure clusters into pre-flight checks.
2. **Citation graph analytics** &mdash; Gini freshness, density per
   section, self-cite ratio. Anomalies surface in the rigor report.
3. **Counterfactual citation probing** &mdash; for each citation, ask an
   LLM judge whether replacing it with a plausible decoy changes the
   sentence's meaning. Decorative citations get flagged.
4. **Adversarial multi-pass review** &mdash; same reviewer is run twice
   with opposing stances (steelman / break). Agreement is a robustness
   signal; disagreement marks fragile claims.
5. **Semantic revision diff** &mdash; embed every claim sentence between
   revisions; report pairs whose cosine dropped below threshold (silent
   meaning inversion).
6. **Pre-registration replay** &mdash; commit prereg (hypothesis, metric,
   direction, tolerance) before the experiment; auditor replays against
   actual results after.
7. **Provenance ledger + auto-disclosure** &mdash; every sentence carries
   tags for author agent, model, and source context. The auto-disclosure
   pass converts those tags into a journal-ready AI-disclosure paragraph.

What else is in v3.0:

- **13 BYOK providers** &mdash; Anthropic, OpenAI, Google, OpenRouter,
  Together, DeepSeek, Qwen, Moonshot, Zhipu, GigaChat, YandexGPT, Mistral,
  Cohere, plus any self-hosted OpenAI-compatible endpoint.
- **23 publisher templates** bundled at install &mdash; Nature, Elsevier
  CAS, Springer, Taylor & Francis, Frontiers, Wiley, SAGE, PLOS, Cell,
  IEEE, ACM, ACS, MDPI, RevTeX, RSC, Cambridge, OUP, BMJ, JAMA, plus the
  Russian GOST family and a default preprint template.
- **7 languages first-class** &mdash; en, ru, es, de, fr, zh, ja. Each
  has a locale module with hyphenation, citation conventions, and
  language-specific rigor heuristics.
- **Cross-host**: same plugin in Claude Code, Codex CLI, or Gemini CLI.
- **Web UI + IDE plugins**: React 19 web UI with collaborative editing,
  VS Code + JetBrains plugins.
- **Federated palace**: multi-user workspace with per-drawer ACL and
  Yjs-backed concurrent editing.
- **Preprint submission**: arXiv, bioRxiv, OSF, SSRN, generic SWORD.

MIT-licensed. Source: <https://github.com/vedix/vedix>

There's a hosted version at vedix.ai with the Free tier giving every
feature; paid tiers buy only throughput.

What I'd love feedback on:

- The seven rigor mechanisms &mdash; what's missing? What would you add
  as #8?
- The counterfactual citation probe in particular &mdash; the LLM judge
  is the weakest link. Better protocols?
- Benchmark suggestions &mdash; what's a fair way to compare Vedix
  output to a hand-edited draft on rigor metrics?
- Integration ideas &mdash; what would you wire Vedix into?

Happy to dig into design tradeoffs in the comments.
