"""
Shared fixtures for the integration test suite.

These tests exercise the whole application through Flask's test client:
the routes, authentication, role-based access, the database, and the audit
log. They complement the unit tests in test_scoring.py, which test the
scoring engine in isolation.

Each test runs against a fresh, throwaway SQLite file that is seeded with a
small synthetic register, so tests never touch the real dora.db and never
depend on the order in which they run.
"""
import os
import tempfile

import pytest

from app import create_app
from app.models import db, User, Provider, Contract, BusinessFunction, ScoringWeight


def _seed():
    """Insert a small, realistic synthetic register: three users (one per
    role), the default scoring weights, two business functions, and three
    providers with one contract each."""
    # One user per role. Passwords are stored as salted hashes, never in plain text.
    for username, role in [("admin", "admin"), ("editor", "editor"), ("viewer", "viewer")]:
        u = User(username=username, role=role)
        u.set_password("password123")
        db.session.add(u)

    # Default scoring weights (normally created by seed.py).
    for name, value in [("criticality", 0.50), ("concentration", 0.30), ("substitutability", 0.20)]:
        db.session.add(ScoringWeight(name=name, value=value))

    # Two business functions, one critical and one non-critical.
    core = BusinessFunction(name="Core banking", criticality="Critical")
    desk = BusinessFunction(name="Internal helpdesk", criticality="None")
    db.session.add_all([core, desk])
    db.session.flush()  # assigns core.id and desk.id

    # Three providers, each with a single contract.
    seed_rows = [
        # name, country, substitutability, contract ref, annual value, function id
        ("CocoCloud", "IE", 5, "CTR-0001", 600000.0, core.id),
        ("PlumSwitch", "LU", 4, "CTR-0002", 250000.0, core.id),
        ("DeskHelp", "LU", 1, "CTR-0003", 40000.0, desk.id),
    ]
    for name, country, sub, ref, value, fid in seed_rows:
        p = Provider(name=name, country=country, substitutability=sub)
        db.session.add(p)
        db.session.flush()  # assigns p.id
        db.session.add(Contract(reference=ref, annual_value=value,
                                provider_id=p.id, function_id=fid))
    db.session.commit()


@pytest.fixture
def app():
    """A fresh application backed by a throwaway SQLite file, seeded per test."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-key",
    })
    with application.app_context():
        db.create_all()
        _seed()

    yield application

    # Teardown. Release the database connection first, otherwise Windows will
    # not let us delete the temp file while SQLAlchemy still holds it open.
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except OSError:
        # On Windows the file handle can linger briefly; the operating system
        # clears its own temp folder, so a failed delete here is harmless.
        pass


@pytest.fixture
def client(app):
    """An anonymous test client (not logged in)."""
    return app.test_client()


def login(test_client, username, password="password123"):
    """Log a client in through the real /login route."""
    return test_client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture
def viewer_client(app):
    """A client logged in as a read-only viewer."""
    c = app.test_client()
    login(c, "viewer")
    return c


@pytest.fixture
def editor_client(app):
    """A client logged in as an editor (can create, edit, and delete)."""
    c = app.test_client()
    login(c, "editor")
    return c


@pytest.fixture
def admin_client(app):
    """A client logged in as an administrator."""
    c = app.test_client()
    login(c, "admin")
    return c
