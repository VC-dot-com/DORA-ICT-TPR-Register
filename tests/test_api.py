"""
Integration tests: the score API, the audit log, and the register export.

These confirm that the read-only JSON API returns a correct breakdown and is
recorded as a disclosure event, that the audit log page renders, and that the
Register of Information exports as CSV and is written to the audit trail.
They exercise inter-module communication: a route queries the database,
calls the scoring engine, and records the access.
"""
from app.models import db, Provider, AuditLog


def _cococloud_id(app):
    with app.app_context():
        return db.session.execute(
            db.select(Provider).filter_by(name="CocoCloud")
        ).scalar_one().id


def test_score_api_returns_a_json_breakdown(admin_client, app):
    pid = _cococloud_id(app)
    resp = admin_client.get(f"/api/providers/{pid}/score")
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    for key in ("provider", "score", "band", "contributions"):
        assert key in body
    assert body["provider"] == "CocoCloud"


def test_score_api_is_recorded_as_a_disclosure(admin_client, app):
    pid = _cococloud_id(app)
    admin_client.get(f"/api/providers/{pid}/score")
    with app.app_context():
        entry = db.session.execute(
            db.select(AuditLog).filter_by(action="API_READ")
        ).scalars().first()
        assert entry is not None


def test_score_api_returns_404_for_an_unknown_provider(admin_client):
    resp = admin_client.get("/api/providers/9999/score")
    assert resp.status_code == 404


def test_audit_log_page_renders(admin_client):
    resp = admin_client.get("/audit")
    assert resp.status_code == 200
    assert b"audit" in resp.data.lower()


def test_register_exports_as_csv(admin_client):
    resp = admin_client.get("/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    assert b"Provider,Country,Supports" in resp.data
    assert b"Portfolio HHI" in resp.data


def test_export_is_recorded_in_the_audit_log(admin_client, app):
    admin_client.get("/export")
    with app.app_context():
        entry = db.session.execute(
            db.select(AuditLog).filter_by(action="EXPORT")
        ).scalars().first()
        assert entry is not None
