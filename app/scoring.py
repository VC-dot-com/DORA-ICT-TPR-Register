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

# HHI bands. Convention drawn from competition policy
# (U.S. Department of Justice & Federal Trade Commission, 2010).
HHI_LOW = 1500
HHI_HIGH = 2500

# Risk band cut-offs on the 0 to 100 scale.
BAND_HIGH = 66
BAND_MEDIUM = 33

# Substitutability is recorded on a 1 to 5 ordinal scale.
SUB_MIN = 1
SUB_MAX = 5

DEFAULT_WEIGHTS = {"criticality": 0.50, "concentration": 0.30, "substitutability": 0.20}


# ---------------------------------------------------------------- validation

def validate_substitutability(value):
    """Substitutability must sit on the 1 to 5 scale, or the score is meaningless."""
    if not isinstance(value, (int, float)):
        raise TypeError("substitutability must be a number")
    if value < SUB_MIN or value > SUB_MAX:
        raise ValueError(
            f"substitutability must be between {SUB_MIN} and {SUB_MAX}, got {value}"
        )
    return value


def normalise_weights(weights):
    """
    Scale the three weights so they sum to 1.

    The weights are stored in the database so a risk officer can tune them.
    Nothing stops that officer entering values that do not sum to 1, which
    would silently break the 0 to 100 scale that the bands depend on.
    Normalising preserves the officer's intended relative emphasis while
    guaranteeing the scale, so a maximally exposed provider always reaches
    100 and is always banded High.
    """
    keys = ("criticality", "concentration", "substitutability")
    values = {k: float(weights.get(k, 0.0)) for k in keys}
    if any(v < 0 for v in values.values()):
        raise ValueError("weights cannot be negative")
    total = sum(values.values())
    if total == 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in values.items()}


# ------------------------------------------------------------------ measures

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
    Sum of squared shares, scaled to the conventional 0 to 10,000 range.
    """
    return sum(s ** 2 for s in dependency_shares(values)) * 10000


def hhi_band(hhi):
    """Plain-language reading of a portfolio HHI."""
    if hhi >= HHI_HIGH:
        return "High concentration"
    if hhi >= HHI_LOW:
        return "Moderate concentration"
    return "Low concentration"


# -------------------------------------------------------------------- scoring

def score_components(supports, share, substitutability):
    """
    The three normalised inputs, each on a 0 to 1 scale, before weighting.
    Separated out so a score can be explained factor by factor.
    """
    validate_substitutability(substitutability)
    return {
        "criticality": criticality_score(supports) / 3.0,
        "concentration": share,
        "substitutability": (substitutability - SUB_MIN) / (SUB_MAX - SUB_MIN),
    }


def provider_score(supports, share, substitutability, weights=None,
                   w_crit=None, w_conc=None, w_sub=None):
    """
    Transparent weighted score, guaranteed to fall between 0 and 100.

    Accepts either a weights dictionary or the three individual weights,
    so existing callers keep working.
    """
    if weights is None:
        weights = {
            "criticality": w_crit if w_crit is not None else DEFAULT_WEIGHTS["criticality"],
            "concentration": w_conc if w_conc is not None else DEFAULT_WEIGHTS["concentration"],
            "substitutability": w_sub if w_sub is not None else DEFAULT_WEIGHTS["substitutability"],
        }
    w = normalise_weights(weights)
    c = score_components(supports, share, substitutability)
    return 100.0 * sum(w[k] * c[k] for k in c)


def explain_score(supports, share, substitutability, weights=None):
    """
    Break a score into the contribution of each factor.

    This is what makes the model defensible to a risk officer or a
    supervisor: the number is never a black box, because every point
    can be traced back to criticality, concentration, or substitutability.
    """
    w = normalise_weights(weights or DEFAULT_WEIGHTS)
    c = score_components(supports, share, substitutability)
    contributions = {k: 100.0 * w[k] * c[k] for k in c}
    total = sum(contributions.values())
    drivers = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "score": round(total, 1),
        "band": risk_band(total),
        "contributions": {k: round(v, 1) for k, v in contributions.items()},
        "weights_applied": {k: round(v, 3) for k, v in w.items()},
        "primary_driver": drivers[0][0],
    }


def risk_band(score):
    """Traffic-light band for a provider score."""
    if score >= BAND_HIGH:
        return "High"
    if score >= BAND_MEDIUM:
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
        score = provider_score(p["supports"], share, p["substitutability"], weights=weights)
        rows.append({
            "name": p["name"],
            "supports": p["supports"],
            "share": share,
            "hhi_contribution": share ** 2,
            "score": round(score, 1),
            "band": risk_band(score),
        })
    return rows, hhi
