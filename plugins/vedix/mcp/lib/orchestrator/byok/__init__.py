"""BYOK (Bring-Your-Own-Key) multi-provider abstraction.

Exposes a unified ``ProviderAdapter`` protocol over 14 LLM providers, a
``ProviderRouter`` with fallback-chain dispatch, and a JSONL cost ledger.
See ``docs/specs/2026-04-30-v3-major-release-spec.md`` §3.2.
"""
