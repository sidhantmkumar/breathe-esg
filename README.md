# Breathe ESG — Data Review Platform

A Django REST and React application that ingests ESG emissions data
from three sources, normalizes it, validates it, and gives analysts
a review dashboard to approve, reject, and edit data before export to auditors.

---

## Live Demo

URL: https://web-production-fa673.up.railway.app

Login credentials:
Username: analyst
Password: Esg@2024

Open the URL in your browser.
Enter the username and password above.
Click Sign in.
You will land on the Overview dashboard with Acme Corp already set up.
No admin setup needed.

---

## Features

### 1. Dashboard Overview
Shows live summary of all data in the system.
- Total approved rows locked for audit
- Total flagged rows needing attention
- Total suspicious rows in review queue
- Total records in staging layer
- Breakdown by Scope 1, Scope 2, Scope 3
- Breakdown by source: SAP, Utility, Travel

### 2. Upload Data Files
Click Upload in the left sidebar.
Select Acme Corp as the company.
Select the source type: SAP Fuel, Utility, or Travel.
Upload your file and click Upload and Process.
System automatically parses, normalizes, and validates every row.
Clean rows are auto-approved and locked.
Suspicious rows go to the Needs Review queue.

Sample files to upload for testing:
- sample_data/sample_sap_data.csv for SAP source
- sample_data/sample_utility_data.csv for Utility source
- sample_data/sample_travel_data.json for Travel source

### 3. All Records
Click All Records in the left sidebar.
See every uploaded row with full details.
Each row shows:
- Source type: SAP, Utility, or Travel
- Scope: 1, 2, or 3
- Category: stationary combustion, purchased electricity, air travel etc
- Raw value and unit exactly as uploaded
- Normalized CO2e in kg
- Reporting period
- Status badge: validated, flagged, approved, rejected
- Flag badge if row was suspicious
- Edited badge if analyst manually changed a value
- Locked badge if row is approved and locked

Filter rows by:
- Status: All, Validated, Flagged, Suspicious, Approved, Rejected
- Source: All Sources, SAP, Utility, Travel

Actions on each row:
- Approve: locks the row for audit
- Reject: marks row as rejected, excluded from export
- Edit: change values, must provide override reason

### 4. Needs Review Queue
Click Needs Review in the left sidebar.
Shows only rows flagged by the validation engine.
Three automatic validation rules:
- Negative values: consumption cannot be negative
- Missing required fields: cannot normalize without them
- Suspicious spike: value more than 3x the batch average
Each flagged row shows the exact reason it was flagged.
Analyst can approve or reject each flagged row.

### 5. Edit a Row
Click Edit on any unlocked row in All Records.
Change the normalized CO2e value if needed.
You must provide an override reason explaining why.
Optionally add analyst notes.
Click Save Changes.
The edit is recorded in the audit log with before and after values.
Row is marked as edited with a badge.

### 6. Upload History
Click Upload History in the left sidebar.
See every file that was ever uploaded.
Each batch shows file name, company, source type, status, uploaded by, date.
Actions on each batch:
- Reject All: rejects entire batch if data quality is too poor
- Export: downloads approved rows as CSV and finalizes the batch

### 7. Export Approved Data
Click Upload History in sidebar.
Find your batch and click Export.
A CSV file downloads with all approved rows from that batch.
Batch status changes to Finalized.
All approved rows become permanently locked.

Export CSV columns:
id, source type, category, scope, raw value, raw unit,
normalized co2e, normalized unit, period start, period end, is edited, created at

### 8. Audit Log
Click Audit Log in the left sidebar.
Every single action is recorded here.
Shows: action type, who performed it, which record, timestamp.
Action types recorded:
- approved: row approved by analyst or system
- rejected: row rejected
- edited: row value changed by analyst
- exported: batch exported and finalized
- batch rejected: entire batch rejected
Audit log is immutable. Nothing here can ever be edited or deleted.

---

## Data Sources Supported

### SAP Fuel and Procurement
File format: CSV, semicolon delimited
Modeled on real SAP MB51 Material Document List export
German column headers: Buchungsdatum, Werk, Menge, Einheit, Bewegungsart
Units handled: L (litres), KL (kilolitres), GAL (US gallons)
Dates handled: DD.MM.YYYY German format
Scope 1 direct emissions
Emission factor: 2.68 kg CO2e per litre of diesel

### Utility Electricity
File format: CSV, comma delimited
Portal export format
Units handled: kWh and MWh mixed in same file
Billing periods not aligned to calendar months handled correctly
Scope 2 purchased electricity
Emission factor: 0.233 kg CO2e per kWh

### Corporate Travel
File format: JSON
Modeled on Concur and Navan API response format
Airport IATA codes converted to distances using haversine formula
Cabin class factors applied: economy, business (2x), first class (4x)
Radiative forcing index 1.891 applied to all flights
Hotel stays: 20.8 kg CO2e per room night (DEFRA 2024)
Ground transport: taxi and rail factors applied
Scope 3 indirect emissions

---

## Running Locally

Requirements:
Python 3.13
PostgreSQL database

Steps:
pip install -r requirements.txt
python manage.py migrate
python create_demo_data.py
python manage.py runserver

Open http://127.0.0.1:8000
Login with analyst / analyst123

---

## Project Structure

api/models.py — 5 core database models
api/views.py — all API endpoints
api/serializers.py — data serialization
api/validators.py — 3 rule automatic validation engine
api/parsers/sap_parser.py — SAP CSV parser
api/parsers/utility_parser.py — Utility CSV parser
api/parsers/travel_parser.py — Travel JSON parser
templates/index.html — complete React frontend
sample_data/ — sample files for all 3 sources
MODEL.md — full data model explanation
DECISIONS.md — every decision made and why
TRADEOFFS.md — three things not built and why
SOURCES.md — real world format research

---

## Architecture

Two Layer Architecture:
Staging layer holds every uploaded row including rejected ones.
Final layer is approved and locked rows only exported to auditors.
Nothing is ever physically deleted from the database.

Multi Tenancy:
Every record belongs to a client company.
Every API query filters by client ID.
One company never sees another companys data.

Audit Trail:
Every action creates an immutable audit log entry.
Before and after state stored as complete JSON snapshots.
Audit logs can never be edited or deleted.

Approval Locking:
Once a row is approved it is locked.
Locked rows cannot be silently edited.
Any change requires override reason and creates audit log entry.

Soft Delete:
Nothing is physically deleted from the database ever.
is_deleted flag used instead.
Full history always preserved for auditors.

Validation Engine:
Three automatic rules run on every upload.
Clean rows auto approved and locked immediately.
Only flagged rows require human review.
System assists analysts, it does not replace them.

---

## Core Philosophy

Simple and thoughtful beats huge and messy.
This system is built around trust, auditability, and traceability.
Humans remain responsible for approval decisions.
The system assists analysts, it does not replace them.