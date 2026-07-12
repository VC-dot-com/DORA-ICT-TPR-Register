"""
Seed the database with SYNTHETIC data only.

These figures reproduce the Unit 2 spreadsheet prototype I developped.
The running application can be checked against the already-validated numbers.
"""
from app import create_app
from app.models import db, User, Provider, Contract, BusinessFunction, ScoringWeight

FUNCTIONS = [
    ("Core banking platform", "Critical"),
    ("Payment processing", "Critical"),
    ("Client data archiving", "Important"),
    ("Corporate email", "Important"),
    ("Document archiving", "Important"),
    ("Internal IT help desk", "None"),
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

USERS = [
    ("admin",  "admin123",  "admin"),
    ("editor", "editor123", "editor"),
    ("viewer", "viewer123", "viewer"),
]

WEIGHTS = [("criticality", 0.50), ("concentration", 0.30), ("substitutability", 0.20)]


def seed():
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
        for name, crit in FUNCTIONS:
            f = BusinessFunction(name=name, criticality=crit)
            db.session.add(f)
            funcs.append(f)
        db.session.flush()

        for i, (name, country, sub, value, fidx) in enumerate(PROVIDERS, start=1):
            p = Provider(name=name, country=country, substitutability=sub)
            db.session.add(p)
            db.session.flush()
            db.session.add(Contract(
                reference=f"CTR-{i:04d}", annual_value=value,
                provider_id=p.id, function_id=funcs[fidx].id,
            ))

        db.session.commit()
        print("Database seeded with synthetic data.")
        print("Logins:  admin/admin123  editor/editor123  viewer/viewer123")


if __name__ == "__main__":
    seed()
