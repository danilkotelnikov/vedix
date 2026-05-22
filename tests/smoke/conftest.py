"""B12 §5 — smoke harness fixtures and marker registration.

Two CLI options plus matching env-var fallbacks supply the live-SaaS
coordinates:

* ``--smoke-saas-url``  / ``VEDIX_SAAS_URL``    — base URL of the SaaS API
  (default: ``http://localhost:8000``).
* ``--smoke-saas-token`` / ``VEDIX_SAAS_TOKEN`` — bearer token (default empty;
  empty causes live tests to skip cleanly).

The ``smoke`` pytest marker is registered here so ``pytest -m smoke`` works
without an external ``pytest.ini`` / ``pyproject.toml`` entry.
"""
from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register CLI flags for the live SaaS URL + token."""
    parser.addoption(
        "--smoke-saas-url",
        action="store",
        default=os.environ.get("VEDIX_SAAS_URL", "http://localhost:8000"),
        help="Base URL of the live Vedix.ai SaaS instance for smoke tests.",
    )
    parser.addoption(
        "--smoke-saas-token",
        action="store",
        default=os.environ.get("VEDIX_SAAS_TOKEN", ""),
        help=(
            "Bearer token for the live SaaS. Empty value causes smoke tests "
            "to skip cleanly."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``smoke`` marker so ``-m smoke`` is recognised."""
    config.addinivalue_line(
        "markers",
        (
            "smoke: cross-block end-to-end smoke against a live Vedix.ai "
            "SaaS deployment. Skips when VEDIX_SAAS_TOKEN is unset."
        ),
    )


@pytest.fixture
def saas_url(request: pytest.FixtureRequest) -> str:
    """Base URL of the live SaaS for the current smoke run."""
    return str(request.config.getoption("--smoke-saas-url"))


@pytest.fixture
def saas_token(request: pytest.FixtureRequest) -> str:
    """Bearer token for the live SaaS, or empty string if unconfigured."""
    return str(request.config.getoption("--smoke-saas-token"))
