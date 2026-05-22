# BYOK providers

Vedix supports 13 first-party providers plus any self-hosted
OpenAI-compatible endpoint. Bring your own key (BYOK) on the CLI or paste it
into the Vedix.ai web UI; the SaaS never persists raw keys, only encrypted
references.

## First-party providers

| Provider | Default model class | Notes |
| --- | --- | --- |
| Anthropic | Claude Opus 4.7 | Recommended default |
| OpenAI | GPT-5 Pro | |
| Google | Gemini 3 Pro | |
| OpenRouter | mixed | Routes to whichever underlying provider |
| Together | mixed open-weight | |
| DeepSeek | DeepSeek-V3 | |
| Qwen | Qwen3-Max | |
| Moonshot | Kimi K2 | |
| Zhipu | GLM-5 | |
| GigaChat (Sber) | GigaChat MAX | Russian language and citation conventions |
| YandexGPT | YandexGPT 5 Pro | Russian language |
| Mistral | Mistral Large 2 | |
| Cohere | Command R+ | |

## Self-hosted

Set `VEDIX_OPENAI_COMPAT_URL` and `VEDIX_OPENAI_COMPAT_KEY` to point Vedix at
any OpenAI-API-compatible endpoint &mdash; vLLM, TGI, Ollama, LM Studio, or
a private deployment of one of the above.

## Configuration

The provider chain is configured in `~/.vedix/config.yaml`:

```yaml
providers:
  default:
    - anthropic
    - openai
    - openrouter
  rigor_review:
    - anthropic
    - openai
  classifier_only:
    - deepseek
```

Chain order is fallback order: if the first provider 429s or times out, Vedix
moves to the next. Per-task chains (`rigor_review`, `classifier_only`, etc.)
override the default.

[Full reference is in development; see `~/.vedix/repo/plugins/vedix/byok/`
for the implementation.]
