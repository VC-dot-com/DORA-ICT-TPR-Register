"""Append-only audit log helper. Insert only: never update, never delete."""
from flask_login import current_user
from .models import db, AuditLog


def record(action, entity):
    username = current_user.username if current_user.is_authenticated else "anonymous"
    db.session.add(AuditLog(username=username, action=action, entity=entity))
    db.session.commit()
