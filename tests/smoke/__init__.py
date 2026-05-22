"""B12 §5 cross-block smoke harness.

Each test in this package is a live-system smoke test &mdash; ie, it talks to
a real running Vedix.ai SaaS deployment via HTTP. The harness skips cleanly
when no ``VEDIX_SAAS_TOKEN`` is provided, so it stays green in unit-test CI
while still being runnable as a pre-release acceptance suite.

Run a smoke pass with::

    pytest -m smoke tests/smoke/ -v

Without ``VEDIX_SAAS_TOKEN`` set, every smoke test SKIPs.
"""
