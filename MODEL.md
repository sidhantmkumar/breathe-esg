# MODEL.md — Data Model

## Core Philosophy
Simple and thoughtful beats huge and messy.
Built around trust, auditability, and traceability.
Humans remain responsible for approval decisions.
The system assists analysts, it does not replace them.

## Five Tables

### Client
Top-level multi-tenancy anchor.
Every other table has a client_id foreign key.
Every query filters by client_id first.
One company never sees another companys data.
- id: UUID primary key (no sequential ID leakage, safe in exports)
- name: display name
- slug: permanent URL-safe identifier, never changes
- timezone: needed to normalize SAP plant-local dates and utility billing dates correctly
- created_at: onboarding timestamp

### DataIngestion (Upload Batch)
Every file upload is tracked as a batch.
Analysts can reject an entire batch if data quality is too poor.
- id: UUID primary key
- client_id: FK to Client
- source_type: sap | utility | travel
- file_name: original uploaded filename
- status: uploaded → under_review → partially_approved → finalized | rejected
- error_log: stores parse errors if file fails to process
- ingested_at: upload timestamp
- ingested_by: username of analyst who uploaded

### EmissionRecord (Core Table — Staging Layer)
Every parsed row from every upload lives here.
Approved rows, rejected rows, flagged rows all coexist here.
Nothing is ever physically deleted.
- id: UUID primary key
- client_id: FK to Client
- ingestion_id: FK to DataIngestion (which upload did this come from)
- scope: 1, 2, or 3 (GHG Protocol classification)
- category: stationary_combustion, purchased_electricity, air_travel, hotel_stay, ground_transport
- source_type: sap | utility | travel
- raw_value: exactly what came in from source file
- raw_unit: exactly what came in (L, KL, GAL, kWh, MWh, km, nights)
- normalized_co2e: computed CO2 equivalent, always in kg CO2e
- normalized_unit: always kg CO2e
- raw_payload: complete original row as JSON, nothing removed
- is_edited: was this row manually corrected by an analyst
- is_suspicious: did validation engine flag this row
- is_locked: approved and locked, no silent edits allowed
- is_deleted: soft delete flag, row never physically removed
- status: uploaded → validated → flagged → approved | rejected
- flag_reason: human readable explanation of why row was flagged
- period_start + period_end: reporting period this row covers
- created_at + updated_at: timestamps

### ReviewStatus
One row per review action on a record.
A single record can be reviewed multiple times.
Full review history preserved separately from the record itself.
- id: UUID primary key
- record_id: FK to EmissionRecord
- status: approved | rejected | flagged | needs_review
- reviewed_by: username of analyst
- notes: free text analyst observations
- override_reason: required when analyst edits a value before approving
- reviewed_at: timestamp

### AuditLog
Immutable ledger of every state change to every record.
Never edited, never deleted, ever.
- id: UUID primary key
- record_id: FK to EmissionRecord (null for batch actions)
- ingestion_id: FK to DataIngestion (for batch level actions)
- action: approved | rejected | edited | flagged | unlocked | batch_rejected | exported
- performed_by: username (system for auto-approvals, analyst name for manual actions)
- before_state: complete JSON snapshot of record before action
- after_state: complete JSON snapshot of record after action
- performed_at: timestamp
- No PUT or DELETE API endpoints exist for this table

## Two Layer Architecture
Staging layer: EmissionRecord table, all rows, all statuses, nothing deleted
Final layer: EmissionRecord rows where status=approved and is_locked=true
Not two separate tables. One table filtered differently.
Rejected rows stay permanently for audit traceability.
Export query selects only approved, locked, non-deleted rows.

## Scope Assignment
SAP fuel and procurement → Scope 1 (direct combustion)
Utility electricity → Scope 2 (purchased electricity)
Flights, hotels, ground transport → Scope 3 (indirect emissions)
Scope assigned automatically during normalization.
Analysts can override during review if assignment is wrong.

## Unit Normalization
All values converted to kg CO2e (kilograms of CO2 equivalent).
L/KL/GAL → litres → multiply by diesel emission factor 2.68 kg CO2e per litre
kWh/MWh → kWh → multiply by grid emission factor 0.233 kg CO2e per kWh
Airport codes → haversine great-circle distance → multiply by cabin class DEFRA factor → multiply by 1.891 RFI
Hotel nights → multiply by 20.8 kg CO2e per room night (DEFRA)
Raw values and units always preserved alongside normalized result.

## Validation Engine
Three automatic rules run on every upload:
1. Negative values: physically impossible for consumption data
2. Missing required fields: cannot normalize without them
3. Suspicious spike: value more than 3x the batch average for that category
Clean rows auto-approve and lock automatically.
Flagged rows go to Needs Review queue for human decision.
Human-readable reason stored per flagged row.
System never auto-rejects. Humans decide.

## Multi-Tenancy
Application-level filtering: every API view filters by client_id from authenticated session.
PostgreSQL Row Level Security mentioned as future production enhancement.
RLS would enforce client_id filtering at database engine level.
Even a raw SQL query from a compromised application could not return another companys data.
Not implemented in prototype due to scope.

## SCD Type 2 Consideration
Considered full historical versioning of every record change (active/inactive rows).
Decided against: too complex for prototype scope.
Replaced by: AuditLog with complete before_state and after_state JSON snapshots.
Same audit capability, much simpler implementation.
Every state change captured. Nothing lost.

## Approval Locking
Once approved: is_locked = true.
Prevents silent editing after approval.
To change an approved row: must explicitly provide override_reason.
That action creates an audit log entry.
This is the trust guarantee of the system.

## Soft Delete
is_deleted = true is the only way to remove something from view.
Nothing is ever physically removed from the database.
Audit trails are meaningless if records can disappear.
Auditors can always see everything that was ever uploaded.

## Why UUID Primary Keys
Sequential integer IDs leak business information.
A user could guess that client 4 exists by trying /api/clients/4/.
UUIDs make enumeration attacks impossible.
Safe to use in exports and audit trails without leaking data.