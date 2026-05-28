# DECISIONS.md — Every Decision Made

## Source 1: SAP Fuel and Procurement

### Decision: Flat File CSV, not IDoc or OData
SAP has four export mechanisms:
- IDoc: requires SAP PI/PO middleware, not realistic without SAP infrastructure
- OData REST API: requires SAP Fiori Gateway and authorization objects configured by BASIS team
- BAPI: requires RFC protocol and live SAP connection
- Flat file: what sustainability analysts actually use today

We chose flat file CSV export from SAP transaction MB51 (Material Document List).
This is how a real sustainability analyst gets data — they ask the SAP team to run a report and send the CSV.

Real column headers in MB51 exports:
- Buchungsdatum: posting date
- Material: material number
- Materialkurztext: material short description
- Werk: plant code (4 character alphanumeric)
- Menge: quantity
- Einheit: unit of measure
- Bewegungsart: movement type (261 = consumption, 101 = goods receipt)

Real problems handled:
- German column headers even when data is in English
- Semicolon delimiter not comma
- Mixed units per plant: L, KL, GAL depending on plant configuration
- Dates in DD.MM.YYYY format (German locale)
- Comma as decimal separator, period as thousands separator
- Movement type filtering needed to avoid double counting procurement vs consumption

What we ignore:
- Purchase order line items
- Vendor master data
- Cost center breakdowns
- Plant hierarchy lookups
- Multi-currency amounts

What I would ask the PM:
- Does client have SAP team who can run standard reports or will sustainability lead do manual exports?
- Are plant codes mapped to geographic locations for grid emission factors?
- Is procurement data separate from consumption data?

## Source 2: Utility Electricity Data

### Decision: Portal CSV Export, not PDF or Utility API
Three realistic modes:
- PDF bills: requires OCR. Fails on scanned PDFs, non-standard layouts, multi-meter consolidated bills. A misread decimal changes emissions significantly. Out of scope.
- Utility API: Green Button standard in US, Smart DCC in UK. Requires OAuth integration per utility. Enterprise clients use 10-20 different utilities. Building per-utility connectors is months of work.
- Portal CSV: most enterprise utility portals offer CSV download. Manual step but what facilities teams actually do today.

Real columns handled:
- account_number, meter_id
- billing_period_start, billing_period_end
- consumption_value, consumption_unit
- tariff_code, facility_name

Real problems handled:
- kWh and MWh mixed in same file
- Billing periods not aligned to calendar months (e.g. Sept 14 to Oct 13)
- Missing consumption values on some rows
- Large data center rows triggering spike detection

Billing period decision:
We store period_start and period_end exactly as they appear in source.
We do not pro-rate into calendar months. That is an analyst judgment call during review.

Grid emission factor used: 0.233 kg CO2e per kWh (average, location-based)

What I would ask the PM:
- Market-based or location-based Scope 2 accounting?
- Does client have renewable energy certificates or PPAs? (changes Scope 2 factor to zero)
- Which grid emission factor and year to use?
- Central facilities team or individual site managers uploading?

## Source 3: Corporate Travel Data

### Decision: JSON modeled on Concur and Navan API response
Travel data is hierarchical. One trip has flights, hotels, and ground transport.
Flat CSV cannot represent this without data duplication or awkward multi-row linking.
JSON is the natural shape of Concur and Navan API responses.

Real fields handled:
- departure_airport, arrival_airport: IATA codes (BOM, LHR, JFK)
- cabin_class: economy, business, first
- travel_date: flight date
- hotel_name, hotel_city, hotel_country, nights, check_in, check_out
- ground transport mode: taxi, rail, car rental
- distance_km for ground transport

Airport codes not distances:
Concur and Navan return IATA airport codes, not distances.
We compute great-circle distance using haversine formula from airport coordinate lookup table.
500 major airports included in lookup table.
Unknown airport codes default to 800km estimate.

DEFRA 2024 emission factors used:
- Economy short haul: 0.15302 kg CO2e per passenger km
- Economy long haul: 0.19085 kg CO2e per passenger km
- Business class: 2x economy factor
- First class: 4x economy factor
- Radiative forcing index: 1.891 multiplier applied to all flights
- Hotel: 20.8 kg CO2e per room night
- Taxi: 0.14930 kg CO2e per km
- Rail: 0.03549 kg CO2e per km

What we ignore:
- Airline-specific emission factors (use DEFRA averages)
- Actual flight paths vs great-circle distance
- Car rental vehicle class and fuel type
- Hotel location-specific grid emission factors

What I would ask the PM:
- Does client use Concur, Navan, or something else? Schema varies slightly.
- Are hotel stays currently tracked or only flight segments?
- DEFRA or ICAO calculator methodology preference?

## Validation Decisions

### 3x spike threshold not 2x or 5x
3x is common in data quality tooling, similar to 3-sigma rule in statistics.
Sensitive enough to catch obvious errors like decimal point in wrong place.
Not so sensitive that it flags natural variation.
Configurable in future as a settings parameter.

### Flagged rows do not auto-reject
Suspicious flags go to Needs Review queue.
Analyst decides. System never auto-rejects.
This is the human-in-the-loop guarantee.

### Clean rows auto-approve
Only flagged rows need human review.
If every row needed manual approval for 20000 row uploads that would be unusable.
Auto-approval with locking is the correct enterprise behavior.

## Architecture Decisions

### Django REST Framework backend, React frontend
DRF gives clean REST API with proper serializers and authentication.
React SPA handles real-time status updates, inline editing, filter interactions.
Clear separation between backend logic and frontend display.

### Django built-in auth, no OAuth
Session login sufficient for prototype.
OAuth (Google, Okta, Azure AD) adds significant setup complexity.
First auth upgrade in production would be enterprise SSO.

### PostgreSQL on Railway
Concurrent reads and writes handled correctly.
UUID primary keys supported natively.
Railway gives zero-config managed PostgreSQL with instant DATABASE_URL.

### UUID primary keys everywhere
No sequential ID leakage.
Safe in exports and audit trails.
Enumeration attacks impossible.

### Soft delete only
ESG data pipeline is an audit system.
Physically deleting records from an audit system is a design error.
If a record was mistakenly uploaded, mark it deleted and log why.
Auditors expect to see everything.

### PostgreSQL RLS as future enhancement
Application-level filtering enforces client isolation today.
RLS would enforce at database engine level in production.
Not implemented due to prototype scope.

### SCD Type 2 replaced by AuditLog
Full historical versioning considered.
Too complex for prototype scope.
AuditLog with before_state and after_state snapshots gives same audit capability.

## What I Would Ask the PM (collected)
1. Market-based or location-based Scope 2?
2. Which grid emission factor and year?
3. DEFRA or GHG Protocol methodology?
4. Calendar year or fiscal year reporting period?
5. Expected upload volume per client?
6. Multiple analysts reviewing same upload or one analyst per batch?
7. Final export format — GHG inventory, CDP submission, or custom template?
8. Does client have RECs or PPAs that affect Scope 2 calculation?

