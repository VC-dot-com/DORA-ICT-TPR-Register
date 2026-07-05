# DORA ICT Third-Party Risk Register and Concentration-Risk Tool

A lightweight web application that helps a financial entity inventory its
ICT third-party arrangements, flag those that support critical or important
functions, score concentration risk, and export a Register of Information
in the supervisory format required under the EU Digital Operational
Resilience Act(DORA).

MSIT 5910 Capstone Project, University of the People. T5-2026

## Status
In development. Unit 3 (detailed design): system architecture, module design,
and version-control setup.

## Technology stack
- Python 3 with the Flask framework
- SQLite database via the SQLAlchemy ORM
- Jinja2 templates and Bootstrap for the interface
- Chart.js for dashboard visualisations
- pytest for automated tests
- Git and GitHub Actions for version control and continuous integration

## Repository structure
- `app/` application source code (Flask application, models, scoring engine)
- `docs/` project documentation (reports, requirements, design notes)
- `design/` design artefacts (architecture diagram, module specs, wireframes)
- `tests/` automated tests

## Data
This project uses synthetic data only. No real client, vendor, or personal
data is used, in line with GDPR and confidentiality requirements.

## Branching
- `main` holds the stable, reviewed version.
- `development` is the working branch where changes are made and tested before
  being merged into `main`.
