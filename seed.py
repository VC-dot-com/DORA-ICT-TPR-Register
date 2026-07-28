"""
Seed the database with SYNTHETIC data only.

Two scenarios share this file, so nothing is ever overwritten:

  python seed.py              loads the canonical 6-provider register
                              (CocoCloud 86.4, portfolio HHI 3,661, High).
                              This is the validated baseline that ties the
                              whole project together, from the Unit 2
                              spreadsheet prototype onward.

  python seed.py --extended   loads a larger 13-provider register (the same
                              6 plus 7 more). The portfolio HHI falls to
                              roughly 1,524 (Moderate) and CocoCloud's share
                              drops to about 31.6%, because concentration is
                              measured relative to the whole portfolio.
                              This demonstrates the tool scaling to a
                              realistic register without any redesign.

Each run rebuilds the database from scratch (drop_all then create_all), so
switching scenarios is just a matter of re-running with or without the flag.
"""
import sys

from app import create_app
from app.models import db, User, Provider, Contract, BusinessFunction, ScoringWeight

# Canonical business functions (indices 0..5).
FUNCTIONS = [
    ("Core banking platform", "Critical"),
    ("Payment processing", "Critical"),
    ("Client data archiving", "Important"),
    ("Corporate email", "Important"),
    ("Document archiving", "Important"),
    ("Internal IT help desk", "None"),
]

# Extra business functions for the extended register (indices 6..12).
EXTRA_FUNCTIONS = [
    ("Cloud storage services", "Important"),
    ("Secondary payment routing", "Critical"),
    ("Network connectivity", "Critical"),
    ("Public web hosting", "None"),
    ("Security operations centre", "Important"),
    ("Data analytics", "None"),
    ("Backup and recovery", "Important"),
]

# provider name, country, substitutability, contract value, function index
PROVIDERS = [
    ("CocoCloud",    "IE", 5, 600000, 0),
    ("PlumSwitch",   "LU", 4, 250000, 1),
    ("NatVault",     "DE", 3, 120000, 2),
    ("SecureV-Mail", "FR", 2,  60000, 3),
    ("DeskHelp",     "BE", 1,  40000, 5),
    ("ArchiveC-Co",  "NL", 2,  30000, 4),
]

# The 7 additional providers, only loaded with --extended.
# Function indices point into FUNCTIONS + EXTRA_FUNCTIONS (so 6..12).
EXTRA_PROVIDERS = [
    ("WisteriaDrives", "SE", 4, 200000,  6),  # cloud storage
    ("LilacPay",       "IT", 3, 150000,  7),  # secondary payments
    ("SparrowNet",     "ES", 4, 130000,  8),  # network connectivity
    ("WagtailHost",    "PL", 2, 110000,  9),  # web hosting
    ("CharlieSOC",     "AT", 3,  90000, 10),  # security monitoring
    ("CurcumaAI",      "PT", 2,  70000, 11),  # data analytics
    ("MartinsVault",   "FI", 3,  50000, 12),  # backup and recovery
]

USERS = [
    ("admin",  "admin123",  "admin"),
    ("editor", "editor123", "editor"),
    ("viewer", "viewer123", "viewer"),
]

WEIGHTS = [("criticality", 0.50), ("concentration", 0.30), ("substitutability", 0.20)]


def seed(extended=False):
    functions = FUNCTIONS + (EXTRA_FUNCTIONS if extended else [])
    providers = PROVIDERS + (EXTRA_PROVIDERS if extended else [])

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        for name, password, role in USERS:
            u = User(username=name, role=role)
            u.set_password(password)
            db.session.add(u)

        for name, value in WEIGHTS:
            db.session.add(ScoringWeight(name=name, value=value))

        funcs = []
        for name, crit in functions:
            f = BusinessFunction(name=name, criticality=crit)
            db.session.add(f)
            funcs.append(f)
        db.session.flush()

        for i, (name, country, sub, value, fidx) in enumerate(providers, start=1):
            p = Provider(name=name, country=country, substitutability=sub)
            db.session.add(p)
            db.session.flush()
            db.session.add(Contract(
                reference=f"CTR-{i:04d}", annual_value=value,
                provider_id=p.id, function_id=funcs[fidx].id,
            ))

        db.session.commit()
        scenario = "extended (13 providers)" if extended else "canonical (6 providers)"
        print(f"Database seeded with synthetic data: {scenario}.")
        print("Logins:  admin/admin123  editor/editor123  viewer/viewer123")


if __name__ == "__main__":
    seed(extended="--extended" in sys.argv)
