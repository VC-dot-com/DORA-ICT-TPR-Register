"""
Automated tests for the concentration-risk scoring engine.

These lock the implementation to the figures validated in the Unit 2
spreadsheet prototype. If the logic ever drifts, these tests fail.
"""
import pytest
from app.scoring import (portfolio_hhi, hhi_band, provider_score,
                         risk_band, score_portfolio, dependency_shares)

WEIGHTS = {"criticality": 0.50, "concentration": 0.30, "substitutability": 0.20}

PORTFOLIO = [
    {"name": "CocoCloud",    "supports": "Critical",  "annual_value": 600000, "substitutability": 5},
    {"name": "PlumSwitch",   "supports": "Critical",  "annual_value": 250000, "substitutability": 4},
    {"name": "NatVault",     "supports": "Important", "annual_value": 120000, "substitutability": 3},
    {"name": "SecureV-Mail", "supports": "Important", "annual_value": 60000,  "substitutability": 2},
    {"name": "DeskHelp",     "supports": "None",      "annual_value": 40000,  "substitutability": 1},
    {"name": "ArchiveC-Co",  "supports": "Important", "annual_value": 30000,  "substitutability": 2},
]


def test_shares_sum_to_one():
    shares = dependency_shares([600000, 250000, 120000, 60000, 40000, 30000])
    assert pytest.approx(sum(shares), abs=1e-9) == 1.0


def test_hhi_matches_prototype():
    values = [p["annual_value"] for p in PORTFOLIO]
    assert portfolio_hhi(values) == pytest.approx(3661, abs=1)


def test_hhi_band_thresholds():
    assert hhi_band(900) == "Low concentration"
    assert hhi_band(2000) == "Moderate concentration"
    assert hhi_band(3661) == "High concentration"


def test_scores_match_prototype():
    """The engine must reproduce the validated spreadsheet figures."""
    expected = {
        "CocoCloud": 86.4, "PlumSwitch": 71.8, "NatVault": 46.6,
        "SecureV-Mail": 40.0, "ArchiveC-Co": 39.2, "DeskHelp": 1.1,
    }
    rows, _ = score_portfolio(PORTFOLIO, WEIGHTS)
    for r in rows:
        assert r["score"] == pytest.approx(expected[r["name"]], abs=0.1)


def test_non_critical_provider_cannot_be_high_risk():
    """Criticality is the dominant factor by design."""
    score = provider_score("None", share=1.0, substitutability=5,
                           w_crit=0.5, w_conc=0.3, w_sub=0.2)
    assert risk_band(score) != "High"


def test_risk_bands():
    assert risk_band(86.4) == "High"
    assert risk_band(46.6) == "Medium"
    assert risk_band(1.1) == "Low"


def test_empty_portfolio_does_not_crash():
    assert portfolio_hhi([]) == 0
    assert dependency_shares([0, 0]) == [0.0, 0.0]


# ------------------------------------------------------------------------
# New regression tests. The weights are stored in the database so a risk
# officer can tune them, but nothing forces them to sum to one. These two
# tests check that the documented 0 to 100 scale actually holds.
# ------------------------------------------------------------------------

def test_score_never_exceeds_100_when_weights_sum_above_one():
    """Weights summing above one must not push a score past the scale maximum."""
    score = provider_score("Critical", share=1.0, substitutability=5,
                           w_crit=0.6, w_conc=0.4, w_sub=0.3)
    assert score <= 100.0


def test_worst_case_provider_is_always_high_risk():
    """
    A provider that supports a critical function, holds the entire portfolio,
    and cannot be replaced is the worst possible case. It must always score
    100 and band High, whatever weights the risk officer has configured.
    """
    score = provider_score("Critical", share=1.0, substitutability=5,
                           w_crit=0.3, w_conc=0.2, w_sub=0.1)
    assert score == pytest.approx(100.0, abs=0.1)
    assert risk_band(score) == "High"
