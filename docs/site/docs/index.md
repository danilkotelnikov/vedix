# Vedix — research workbench, not a chatbot

Vedix is a single-command research workbench. It turns a topic into a
venue-ready manuscript by running literature search, hypothesis design,
experimentation, claim auditing, and publisher-specific typesetting as one
orchestrated pipeline &mdash; with seven rigor mechanisms baked in so the
output is honest before it is polished.

## Install

=== "Linux / macOS"
    ```bash
    curl -fsSL https://vedix.ai/install.sh | bash
    ```

=== "Windows (PowerShell)"
    ```powershell
    iwr -useb https://vedix.ai/install.ps1 | iex
    ```

The bootstrap auto-detects your AI coding assistant (Claude Code, Codex CLI,
Gemini CLI), installs the plugin, registers the 9 MCPs, and fetches the
pre-trained register classifiers (~6 GB; one-time download).

## Run

```text
/vedix linear regression on synthetic data
```

That's it. Vedix walks you through a short setup form, runs the pipeline, and
emits a manuscript in your chosen venue's format.

## What's in v3.0

- **23 publisher templates** bundled at install (Nature, Elsevier, Springer,
  Taylor & Francis, Frontiers, Wiley, SAGE, PLOS, Cell, IEEE, ACM, ACS, MDPI,
  RevTeX, RSC, Cambridge, OUP, BMJ, JAMA, GOST-generic, DAN RAS, Uspekhi,
  Overleaf preprint default).
- **7 languages** first-class: English, Russian (GOST-7.0.5), Spanish, German,
  French, Chinese, Japanese.
- **13 BYOK providers**: Anthropic, OpenAI, Google, OpenRouter, Together,
  DeepSeek, Qwen, Moonshot, Zhipu, GigaChat (Sber), YandexGPT, Mistral, Cohere,
  plus self-hosted OpenAI-compatible.
- **7 rigor tracks**: failure-mode learning, citation graph analytics,
  counterfactual citation probing, adversarial multi-pass review, semantic
  revision diff, pre-registration replay, provenance ledger + auto-disclosure.
- **Cross-host**: Claude Code, Codex CLI, Gemini CLI &mdash; same skill, same
  pipeline.
- **Vedix.ai SaaS**: hosted job queue, hosted MCPs, web UI, IDE plugins. Free
  tier gets everything; paid tiers buy throughput.

## Why a workbench, not a chatbot?

A chatbot will happily write you a polished paragraph that cites a paper that
doesn't exist. Vedix won't. The pipeline structurally separates four
things that AI assistants tend to fuse into a single hallucination:

1. **What the experiment actually produced** (a CSV, a model checkpoint, a
   plot).
2. **What the literature actually says** (full-text retrieval, not abstract
   scraping).
3. **What the author wants to claim** (a hypothesis registered before the
   experiment runs).
4. **What ends up in the manuscript** (every sentence traced back to one of
   the above through the provenance ledger).

The seven rigor mechanisms enforce that separation. Counterfactual citation
probing flags citations that read like padding. Adversarial multi-pass review
runs the same reviewer against the manuscript with two opposing stances and
treats agreement as a robustness signal. The numerical claim audit reads
results.csv before it lets the manuscript reference any number.

## Open source

Vedix is MIT-licensed. [Repo on GitHub](https://github.com/vedix/vedix)
