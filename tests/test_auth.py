"""
Integration tests: authentication and role-based access control.

These confirm that the login flow works, that protected pages are closed to
anonymous users, and that authorisation is enforced on the server. A viewer
must not reach an editor-only route even by requesting the URL directly,
because access is checked on the route rather than by hiding buttons.
"""
from app.models import db, Provider


def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_login_succeeds_with_valid_credentials(client):
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "password123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # After a successful login the user lands on the dashboard.
    assert b"dashboard" in resp.data.lower()


def test_login_fails_with_wrong_password(client):
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_dashboard_requires_login(client):
    # No follow_redirects: an anonymous request is redirected to the login page.
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout_ends_the_session(admin_client):
    resp = admin_client.get("/logout")
    assert resp.status_code == 302
    # After logging out, the dashboard is protected again.
    resp = admin_client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_viewer_cannot_open_the_new_provider_form(viewer_client):
    resp = viewer_client.get("/providers/new")
    assert resp.status_code == 403


def test_viewer_cannot_create_a_provider(viewer_client, app):
    resp = viewer_client.post(
        "/providers/new",
        data={"name": "SneakyCo", "country": "LU", "substitutability": 3},
    )
    assert resp.status_code == 403
    # The forbidden request must not have written anything to the database.
    with app.app_context():
        exists = db.session.execute(
            db.select(Provider).filter_by(name="SneakyCo")
        ).scalar_one_or_none()
        assert exists is None


def test_editor_can_open_the_new_provider_form(editor_client):
    resp = editor_client.get("/providers/new")
    assert resp.status_code == 200
