# DORA ICT Third-Party Risk Register and Concentration-Risk Tool

A lightweight web application that helps a financial entity inventory its ICT
third-party arrangements, flag those supporting critical or important functions,
score concentration risk, and export a Register of Information in the supervisory
format required under the EU Digital Operational Resilience Act (DORA).

MSIT 5910 Capstone Project, University of the People (T5-2026).

## Status
Unit 4: initial implementation. Authentication, provider CRUD, the concentration-risk
scoring engine, the dashboard, the register export, and the audit log are working.

## Architecture
Layered (n-tier), as specified in the Unit 3 design:

| Layer | Responsibility | Implementation |
|---|---|---|
| Presentation | Screens and forms | Jinja2 templates + Bootstrap |
| Business logic | Auth/RBAC, CRUD, scoring, export, audit | Flask blueprints, `app/scoring.py` |
| Data access | Parameterised queries only | SQLAlchemy ORM |
| Database | Seven tables | SQLite |

The presentation layer never reaches the database directly. Every request passes
through the business-logic layer, where authorisation is enforced per route.

## Data model (seven tables)
`users`, `providers`, `contracts`, `business_functions`, `scoring_weights`,
`risk_scores`, `audit_log`

## Scoring methodology
Each provider is scored 0-100 from three inputs:
- **Criticality** (dominant factor): does it support a critical or important function
- **Concentration**: its share of the portfolio, feeding a Herfindahl-Hirschman Index
- **Substitutability**: how hard it would be to replace (1 to 5)

Weights live in the `scoring_weights` table, not in code, so a risk officer can
tune them and every score stays explainable and auditable.

## Quick start
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python seed.py               # loads synthetic data
python run.py                # http://127.0.0.1:5000
```

Logins: `admin/admin123`, `editor/editor123`, `viewer/viewer123`

## Tests
```bash
pytest -v
```
The tests lock the scoring engine to the figures validated in the Unit 2
spreadsheet prototype. GitHub Actions runs them on every push.

## Data
Synthetic data only. No real client, vendor, or personal data is used,
in line with GDPR and confidentiality requirements.
