"""Block 7 Task 1 — venue registry tests (§7).

23 publisher venues are bundled at install. Each has a LaTeX class file
identifier, a citation-style identifier and a region tag (``"global"`` /
``"ru"``). The registry is sourced from
:mod:`plugins.vedix.mcp.lib.orchestrator.publisher_engine`.
"""
from __future__ import annotations

import pytest

from plugins.vedix.mcp.lib.orchestrator.publisher_engine import (
    VENUES,
    Venue,
    get_venue,
    list_venues,
)


def test_23_venues_registered():
    assert len(list_venues()) == 23


def test_list_venues_is_sorted():
    listed = list_venues()
    assert listed == sorted(listed)


def test_list_venues_matches_registry_keys():
    assert set(list_venues()) == set(VENUES)


@pytest.mark.parametrize(
    "venue",
    [
        "preprint",
        "nature",
        "elsevier",
        "springer-nature",
        "taylor-francis",
        "frontiers",
        "wiley",
        "sage",
        "plos",
        "cell",
        "ieee",
        "acm",
        "acs",
        "mdpi",
        "revtex42",
        "rsc",
        "cambridge",
        "oup",
        "bmj",
        "jama",
        "gost-generic",
        "dan-ras",
        "uspekhi",
    ],
)
def test_each_venue_has_class_and_profile(venue):
    v = get_venue(venue)
    assert isinstance(v, Venue)
    assert v.latex_class.endswith(".cls")
    assert v.citation_style
    assert v.region in {"global", "ru"}


def test_both_regions_are_represented():
    regions = {v.region for v in VENUES.values()}
    assert regions == {"global", "ru"}


def test_ru_region_contains_expected_venues():
    ru_venues = {name for name, v in VENUES.items() if v.region == "ru"}
    assert ru_venues == {"gost-generic", "dan-ras", "uspekhi"}


def test_get_venue_strips_journal_suffix():
    """``get_venue("elsevier:cell-host-microbe")`` resolves to base venue."""
    v = get_venue("elsevier:cell-host-microbe")
    assert v.name == "elsevier"


def test_get_venue_raises_for_unknown_name():
    with pytest.raises(KeyError):
        get_venue("not-a-venue")


def test_venues_default_to_bundled():
    for v in VENUES.values():
        assert v.bundled is True
