"""
Data model: the seven tables from the Unit 3 design.

users, providers, contracts, business_functions,
scoring_weights, risk_scores, audit_log
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")  # admin | editor | viewer

    def set_password(self, password):
        # Salted hash. Werkzeug generates a unique salt per password.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit(self):
        return self.role in ("admin", "editor")

    def can_admin(self):
        return self.role == "admin"


class BusinessFunction(db.Model):
    __tablename__ = "business_functions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # DORA: is this a critical or important function?
    criticality = db.Column(db.String(20), nullable=False, default="None")  # Critical|Important|None
    contracts = db.relationship("Contract", back_populates="function")


class Provider(db.Model):
    __tablename__ = "providers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    country = db.Column(db.String(64))
    # 1 = easy to replace .. 5 = very hard to replace (DORA replaceability)
    substitutability = db.Column(db.Integer, nullable=False, default=3)
    contracts = db.relationship("Contract", back_populates="provider",
                                cascade="all, delete-orphan")

    @property
    def annual_value(self):
        return sum(c.annual_value for c in self.contracts)

    @property
    def supports(self):
        """Highest criticality among the functions this provider supports."""
        levels = [c.function.criticality for c in self.contracts if c.function]
        if "Critical" in levels:
            return "Critical"
        if "Important" in levels:
            return "Important"
        return "None"


class Contract(db.Model):
    __tablename__ = "contracts"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(64), nullable=False)
    annual_value = db.Column(db.Float, nullable=False, default=0.0)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False)
    function_id = db.Column(db.Integer, db.ForeignKey("business_functions.id"))
    provider = db.relationship("Provider", back_populates="contracts")
    function = db.relationship("BusinessFunction", back_populates="contracts")


class ScoringWeight(db.Model):
    """Weights live in the database, not in code, so they can be tuned and audited."""
    __tablename__ = "scoring_weights"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    value = db.Column(db.Float, nullable=False)


class RiskScore(db.Model):
    """Dated history of computed scores, complementing the audit log."""
    __tablename__ = "risk_scores"
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    band = db.Column(db.String(10), nullable=False)
    computed_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    provider = db.relationship("Provider")


class AuditLog(db.Model):
    """Append-only. Records are inserted, never updated or deleted."""
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(40), nullable=False)     # CREATE | UPDATE | DELETE | EXPORT | LOGIN
    entity = db.Column(db.String(120), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
