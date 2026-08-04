"""
Integration tests: provider CRUD and the dashboard.

These drive the create, read, update, and delete routes as an editor and
confirm that the dashboard and the provider list render the seeded register.
Together they show the user interface, the business logic, and the database
working as one system rather than as isolated units.
"""
from app.models import db, Provider


def test_dashboard_renders_the_register(editor_client):
    resp = editor_client.get("/")
    assert resp.status_code == 200
    assert b"CocoCloud" in resp.data
    # The portfolio concentration reading is shown on the dashboard.
    assert b"HHI" in resp.data or b"concentration" in resp.data.lower()


def test_provider_list_shows_seeded_providers(editor_client):
    resp = editor_client.get("/providers")
    assert resp.status_code == 200
    for name in (b"CocoCloud", b"PlumSwitch", b"DeskHelp"):
        assert name in resp.data


def test_provider_detail_page_renders(editor_client, app):
    with app.app_context():
        pid = db.session.execute(
            db.select(Provider).filter_by(name="CocoCloud")
        ).scalar_one().id
    resp = editor_client.get(f"/providers/{pid}")
    assert resp.status_code == 200
    assert b"CocoCloud" in resp.data


def test_editor_can_create_a_provider(editor_client, app):
    resp = editor_client.post(
        "/providers/new",
        data={"name": "NimbusPay", "country": "LU",
              "substitutability": 2, "annual_value": "120000", "function_id": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        created = db.session.execute(
            db.select(Provider).filter_by(name="NimbusPay")
        ).scalar_one_or_none()
        assert created is not None


def test_editor_can_edit_a_provider(editor_client, app):
    with app.app_context():
        pid = db.session.execute(
            db.select(Provider).filter_by(name="DeskHelp")
        ).scalar_one().id
    resp = editor_client.post(
        f"/providers/{pid}/edit",
        data={"name": "DeskHelpPlus", "country": "LU", "substitutability": 2},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        renamed = db.session.get(Provider, pid)
        assert renamed.name == "DeskHelpPlus"


def test_editor_can_delete_a_provider(editor_client, app):
    with app.app_context():
        pid = db.session.execute(
            db.select(Provider).filter_by(name="PlumSwitch")
        ).scalar_one().id
    resp = editor_client.post(f"/providers/{pid}/delete", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Provider, pid) is None
