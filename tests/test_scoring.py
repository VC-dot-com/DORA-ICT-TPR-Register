"""
Automated tests for the concentration-risk scoring engine.

These lock the implementation to the figures validated in the Unit 2
spreadsheet prototype, and guard the invariants the design depends on.
If the logic ever drifts, these tests fail.
"""
import pytest
from app.scoring import (portfolio_hhi, hhi_band, provider_score, risk_band,
                         score_portfolio, dependency_shares, normalise_weights,
                         validate_substitutability, explain_score, score_components)

WEIGHTS = {"criticality": 0.50, "concentration": 0.30, "substitutability": 0.20}

PORTFOLIO = [
    {"name": "CocoCloud",    "supports": "Critical",  "annual_value": 600000, "substitutability": 5},
    {"name": "PlumSwitch",   "supports": "Critical",  "annual_value": 250000, "substitutability": 4},
    {"name": "NatVault",     "supports": "Important", "annual_value": 120000, "substitutability": 3},
    {"name": "SecureV-Mail", "supports": "Important", "annual_value": 60000,  "substitutability": 2},
    {"name": "DeskHelp",     "supports": "None",      "annual_value": 40000,  "substitutability": 1},
    {"name": "ArchiveC-Co",  "supports": "Important", "annual_value": 30000,  "substitutability": 2},
]


# --------------------------------------------------- concentration measurement

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


def test_empty_portfolio_does_not_crash():
    assert portfolio_hhi([]) == 0
    assert dependency_shares([0, 0]) == [0.0, 0.0]


# ------------------------------------------------------------ provider scoring

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
    score = provider_score("None", share=1.0, substitutability=5, weights=WEIGHTS)
    assert risk_band(score) != "High"


def test_risk_bands():
    assert risk_band(86.4) == "High"
    assert risk_band(46.6) == "Medium"
    assert risk_band(1.1) == "Low"


# ------------------------------------------- weight handling (regression tests)

def test_weights_are_normalised_to_sum_to_one():
    w = normalise_weights({"criticality": 0.6, "concentration": 0.4, "substitutability": 0.3})
    assert pytest.approx(sum(w.values()), abs=1e-9) == 1.0


def test_score_never_exceeds_100_when_weights_sum_above_one():
    """Regression: weights summing above 1 previously produced scores over 100."""
    inflated = {"criticality": 0.6, "concentration": 0.4, "substitutability": 0.3}
    score = provider_score("Critical", share=1.0, substitutability=5, weights=inflated)
    assert score <= 100.0


def test_worst_case_provider_is_always_high_risk():
    """
    Regression: weights summing below 1 previously under-scored the worst
    provider, banding a critical, unreplaceable, sole provider as Medium.
    """
    deflated = {"criticality": 0.3, "concentration": 0.2, "substitutability": 0.1}
    score = provider_score("Critical", share=1.0, substitutability=5, weights=deflated)
    assert score == pytest.approx(100.0, abs=0.1)
    assert risk_band(score) == "High"


def test_relative_emphasis_is_preserved_after_normalisation():
    """Doubling every weight must not change any resulting score."""
    doubled = {k: v * 2 for k, v in WEIGHTS.items()}
    base = provider_score("Critical", 0.5, 4, weights=WEIGHTS)
    scaled = provider_score("Critical", 0.5, 4, weights=doubled)
    assert base == pytest.approx(scaled, abs=1e-9)


def test_zero_weights_fall_back_to_defaults():
    w = normalise_weights({"criticality": 0, "concentration": 0, "substitutability": 0})
    assert pytest.approx(sum(w.values()), abs=1e-9) == 1.0


def test_negative_weights_are_rejected():
    with pytest.raises(ValueError):
        normalise_weights({"criticality": -0.5, "concentration": 0.3, "substitutability": 0.2})


# ------------------------------------------------------------ input validation

def test_substitutability_outside_scale_is_rejected():
    with pytest.raises(ValueError):
        validate_substitutability(7)
    with pytest.raises(ValueError):
        validate_substitutability(0)


def test_substitutability_accepts_the_full_scale():
    for v in (1, 2, 3, 4, 5):
        assert validate_substitutability(v) == v


# -------------------------------------------------------------- explainability

def test_explain_score_contributions_sum_to_the_score():
    result = explain_score("Critical", 0.545, 5, WEIGHTS)
    assert pytest.approx(sum(result["contributions"].values()), abs=0.2) == result["score"]


def test_explain_score_identifies_the_primary_driver():
    """A critical but tiny, replaceable provider is driven by criticality."""
    result = explain_score("Critical", 0.01, 1, WEIGHTS)
    assert result["primary_driver"] == "criticality"


def test_components_are_all_on_a_zero_to_one_scale():
    c = score_components("Critical", 0.5, 5)
    assert all(0.0 <= v <= 1.0 for v in c.values())
