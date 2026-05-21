"""Typed exceptions for the BYOK layer.

These map provider-specific errors onto a small uniform set that the router
can pattern-match on for fallback decisions.
"""
from __future__ import annotations


class BYOKError(Exception):
    """Base class for all BYOK errors."""


class RateLimited(BYOKError):
    def __init__(self, provider: str, retry_after: float | None = None):
        super().__init__(f"{provider} rate-limited")
        self.provider = provider
        self.retry_after = retry_after


class ContextOverflow(BYOKError):
    def __init__(self, provider: str, max_context: int, requested: int):
        super().__init__(f"{provider} max_context={max_context}, requested={requested}")
        self.provider = provider
        self.max_context = max_context
        self.requested = requested


class ProviderUnavailable(BYOKError):
    def __init__(self, provider: str, reason: str):
        super().__init__(f"{provider} unavailable: {reason}")
        self.provider = provider
        self.reason = reason


class AuthError(BYOKError):
    def __init__(self, provider: str):
        super().__init__(f"{provider} auth failed")
        self.provider = provider


class CapabilityMissing(BYOKError):
    def __init__(self, provider: str, capability: str):
        super().__init__(f"{provider} lacks capability: {capability}")
        self.provider = provider
        self.capability = capability
