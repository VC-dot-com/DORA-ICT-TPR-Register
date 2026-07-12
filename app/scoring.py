"""
Concentration-risk scoring engine.

Implements the methodology validated in the Unit 2 spreadsheet prototype:
  - Criticality: does the provider support a critical or important function
  - Concentration: the provider's share of the portfolio (feeds the HHI)
  - Substitutability: how hard the provider is to replace (1 easy .. 5 hard)

Pure functions with no framework dependencies, so they can be unit tested
in isolation. This is the layered architecture in practice: the business
logic does not know about Flask or the database.
"""

CRITICALITY_SCORES = {"Critical": 3, "Important": 2, "None": 0}

# HHI bands (convention drawn from competition policy)
HHI_LOW = 1500
HHI_HIGH = 2500


def criticality_score(supports):
    """Map a criticality label to its ordinal score."""
    return CRITICALITY_SCORES.get(supports, 0)


def dependency_shares(values):
    """Each provider's share of total annual contract value."""
    total = sum(values)
    if total == 0:
        return [0.0 for _ in values]
    return [v / total for v in values]


def portfolio_hhi(values):
    """
    Herfindahl-Hirschman Index across the provider portfolio.
    Sum of squared shares, scaled to the conventional 0-10,000 range.
    """
    return sum(s ** 2 for s in dependency_shares(values)) * 10000


def hhi_band(hhi):
    """Plain-language reading of a portfolio HHI."""
    if hhi >= HHI_HIGH:
        return "High concentration"
    if hhi >= HHI_LOW:
        return "Moderate concentration"
    return "Low concentration"


def provider_score(supports, share, substitutability, w_crit, w_conc, w_sub):
    """
    Transparent weighted score, 0 to 100.

    Every term is normalised to 0..1 before weighting, so the result is
    explainable: a risk officer can see exactly what drove the number.
    """
    c = criticality_score(supports) / 3.0          # 0..1
    s = (substitutability - 1) / 4.0               # 1..5 -> 0..1
    return 100.0 * (w_crit * c + w_conc * share + w_sub * s)


def risk_band(score):
    """Traffic-light band for a provider score."""
    if score >= 66:
        return "High"
    if score >= 33:
        return "Medium"
    return "Low"


def score_portfolio(providers, weights):
    """
    Score a whole portfolio.

    providers: list of dicts with keys name, supports, annual_value, substitutability
    weights:   dict with keys criticality, concentration, substitutability

    Returns (scored_rows, portfolio_hhi).
    """
    values = [p["annual_value"] for p in providers]
    shares = dependency_shares(values)
    hhi = portfolio_hhi(values)

    rows = []
    for p, share in zip(providers, shares):
        score = provider_score(
            p["supports"], share, p["substitutability"],
            weights["criticality"], weights["concentration"], weights["substitutability"],
        )
        rows.append({
            "name": p["name"],
            "supports": p["supports"],
            "share": share,
            "hhi_contribution": share ** 2,
            "score": round(score, 1),
            "band": risk_band(score),
        })
    return rows, hhi
