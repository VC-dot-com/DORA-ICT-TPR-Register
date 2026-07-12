"""Business-logic layer: dashboard, provider CRUD, and register export."""
import csv
import io
from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, Response)
from flask_login import login_required, current_user

from .models import db, Provider, Contract, BusinessFunction, ScoringWeight, RiskScore
from .scoring import score_portfolio, hhi_band
from .auth import editor_required
from . import audit

main_bp = Blueprint("main", __name__)


def current_weights():
    """Weights are read from the database, so they are tunable and auditable."""
    rows = db.session.execute(db.select(ScoringWeight)).scalars().all()
    w = {r.name: r.value for r in rows}
    return {
        "criticality": w.get("criticality", 0.50),
        "concentration": w.get("concentration", 0.30),
        "substitutability": w.get("substitutability", 0.20),
    }


def compute_scores(persist=False):
    """Run the scoring engine over every provider in the register."""
    providers = db.session.execute(db.select(Provider)).scalars().all()
    if not providers:
        return [], 0.0

    payload = [{
        "name": p.name,
        "supports": p.supports,
        "annual_value": p.annual_value,
        "substitutability": p.substitutability,
    } for p in providers]

    rows, hhi = score_portfolio(payload, current_weights())

    if persist:
        for p, r in zip(providers, rows):
            db.session.add(RiskScore(provider_id=p.id, score=r["score"], band=r["band"]))
        db.session.commit()

    for p, r in zip(providers, rows):
        r["id"] = p.id
        r["country"] = p.country
        r["annual_value"] = p.annual_value
        r["substitutability"] = p.substitutability
    return rows, hhi


@main_bp.route("/")
@login_required
def dashboard():
    rows, hhi = compute_scores(persist=True)
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    critical_count = sum(1 for r in rows if r["supports"] in ("Critical", "Important"))
    return render_template(
        "dashboard.html",
        rows=rows, hhi=hhi, hhi_reading=hhi_band(hhi),
        critical_count=critical_count,
        weights=current_weights(),
    )


@main_bp.route("/providers")
@login_required
def providers():
    rows = db.session.execute(db.select(Provider).order_by(Provider.name)).scalars().all()
    return render_template("providers.html", providers=rows)


@main_bp.route("/providers/new", methods=["GET", "POST"])
@editor_required
def provider_new():
    functions = db.session.execute(db.select(BusinessFunction)).scalars().all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Provider name is required.", "danger")
            return render_template("provider_form.html", provider=None, functions=functions)

        p = Provider(
            name=name,
            country=request.form.get("country", "").strip(),
            substitutability=int(request.form.get("substitutability", 3)),
        )
        db.session.add(p)
        db.session.flush()

        # optional first contract
        value = request.form.get("annual_value", "").strip()
        fid = request.form.get("function_id", "")
        if value:
            db.session.add(Contract(
                reference=request.form.get("reference", "").strip() or f"CTR-{p.id:04d}",
                annual_value=float(value),
                provider_id=p.id,
                function_id=int(fid) if fid else None,
            ))
        db.session.commit()
        audit.record("CREATE", f"provider:{p.name}")
        flash(f"Provider '{p.name}' added. Scores recomputed.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("provider_form.html", provider=None, functions=functions)


@main_bp.route("/providers/<int:pid>/edit", methods=["GET", "POST"])
@editor_required
def provider_edit(pid):
    p = db.session.get(Provider, pid)
    if not p:
        flash("Provider not found.", "danger")
        return redirect(url_for("main.providers"))
    functions = db.session.execute(db.select(BusinessFunction)).scalars().all()

    if request.method == "POST":
        p.name = request.form.get("name", p.name).strip()
        p.country = request.form.get("country", p.country).strip()
        p.substitutability = int(request.form.get("substitutability", p.substitutability))
        db.session.commit()
        audit.record("UPDATE", f"provider:{p.name}")
        flash(f"Provider '{p.name}' updated.", "success")
        return redirect(url_for("main.providers"))

    return render_template("provider_form.html", provider=p, functions=functions)


@main_bp.route("/providers/<int:pid>/delete", methods=["POST"])
@editor_required
def provider_delete(pid):
    p = db.session.get(Provider, pid)
    if p:
        name = p.name
        db.session.delete(p)
        db.session.commit()
        audit.record("DELETE", f"provider:{name}")
        flash(f"Provider '{name}' deleted.", "success")
    return redirect(url_for("main.providers"))


@main_bp.route("/export")
@login_required
def export():
    """Register of Information export. Access-checked and audit-logged."""
    rows, hhi = compute_scores()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Provider", "Country", "Supports", "Annual value (EUR)",
                "Substitutability", "Value share", "Risk score", "Band"])
    for r in rows:
        w.writerow([r["name"], r["country"], r["supports"], f'{r["annual_value"]:.2f}',
                    r["substitutability"], f'{r["share"]:.4f}', r["score"], r["band"]])
    w.writerow([])
    w.writerow(["Portfolio HHI", f"{hhi:.0f}", hhi_band(hhi)])

    audit.record("EXPORT", "register_of_information")
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=register_of_information.csv"},
    )


@main_bp.route("/audit")
@login_required
def audit_view():
    from .models import AuditLog
    entries = db.session.execute(
        db.select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50)
    ).scalars().all()
    return render_template("audit.html", entries=entries)
