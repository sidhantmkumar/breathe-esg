# SOURCES.md — Real World Research Per Source

## Source 1: SAP Fuel and Procurement

### What was researched
SAP MB51 Material Document List transaction.
This is the standard SAP transaction for viewing material movements.
When a company tracks fuel procurement and consumption through SAP Materials Management,
MB51 is how a sustainability analyst gets the raw consumption data.
Export via SAP GUI: List → Export → Spreadsheet gives flat file CSV.

Also researched:
- SAP IDoc format (EDI XML-like, requires middleware)
- SAP OData REST API (requires Fiori Gateway)
- SAP BAPI function calls (requires RFC protocol)
- SAP Integration Suite connectors

Chose flat file because it is what analysts actually use without IT involvement.

### Real column headers in MB51 German configuration
- Buchungsdatum: posting date
- Material: material number (internal code)
- Materialkurztext: material short description
- Werk: plant code (4 character like 1000, IN01, US50)
- Lagerort: storage location
- Menge: quantity
- Einheit: unit of measure (L, KL, GAL, IGAL, TO, GJ)
- Bewegungsart: movement type (261 consumption, 101 goods receipt)
- Belegjahr: fiscal year
- Buchungsperiode: posting period

### Real inconsistencies found in research
- Same material appears in L on some rows and KL on others depending on plant configuration
- Some international plants use GAL (US gallons) or IGAL (Imperial gallons)
- Steam and heat appear in GJ or MMBTU
- German locale: comma as decimal separator, period as thousands separator
- Dates in DD.MM.YYYY format
- German column headers even when plant data is in English
- System does not enforce unit consistency across plants

### What our sample data looks like and why
File: sample_sap_data.csv
Format: semicolon delimited, German column headers
Contents:
- Mix of L, KL, and GAL units across rows (tests unit normalization)
- Plant codes: 1000 (Germany), IN01 (India), US50 (USA)
- Dates in DD.MM.YYYY format
- One row with negative Menge value (triggers negative value validation rule)
- One row with 5000L when average is around 500L (triggers spike detection rule)
- Movement type 261 throughout (consumption not procurement)

### What would break in real deployment
- Plant code lookup: Werk codes need mapping to facility names and geographic locations
- Movement type filtering: goods receipt (101) looks like consumption in raw data
- Material master lookup: material numbers need resolving to human readable fuel types
- Decimal separator: German locale exports need special parsing
- Multi-currency: SAP records values in local plant currency

---

## Source 2: Utility Electricity Data

### What was researched
Green Button standard (US Department of Energy initiative):
- XML format (ESPI standard) or CSV
- Values in Wh not kWh in raw Green Button format (divide by 1000)
- Utilities: PG&E, Con Edison, many US utilities

UK Power Networks and UK utilities:
- MPAN (Meter Point Administration Number) as meter identifier
- Half-hourly settlement data: 48 rows per meter per day
- 100 meters across UK facilities = 4800 rows per day

Indian utilities (Tata Power, BSES, MSEDCL enterprise portals):
- consumer_number, billing_month, unit_consumed, unit
- Units inconsistent: large commercial accounts bill in MWh, small accounts in kWh

Key finding on billing periods:
Utility billing periods follow meter reading schedules not calendar months.
A meter read on the 14th means September bill covers August 14 to September 13.
This creates attribution ambiguity for annual GHG reporting.

### Real columns handled
account_number, meter_id, billing_period_start, billing_period_end,
consumption_value, consumption_unit, tariff_code, facility_name

### What our sample data looks like and why
File: sample_utility_data.csv
Format: comma delimited, ISO 8601 dates (YYYY-MM-DD)
Contents:
- Mix of kWh and MWh in same file (small offices vs large industrial)
- Billing periods not aligned to calendar months (14th to 13th pattern)
- Four facilities: Mumbai Office, Mumbai Warehouse, Delhi Office, Delhi Factory
- One row with empty consumption_value (triggers missing field validation)
- One Bangalore Data Center row with 95000 kWh (triggers spike detection)
- One MWh row to test unit conversion to kWh

Grid emission factor used: 0.233 kg CO2e per kWh (average location-based)

### What would break in real deployment
- Grid emission factor varies by country, region, and year
  UK: 0.207 kg CO2e per kWh (2024)
  India average: 0.82 kg CO2e per kWh (varies by state)
- Market-based vs location-based Scope 2: RECs or PPAs make factor zero
- Half-hourly data volume: millions of rows annually for large UK enterprise
- Multi-site consolidated bills need account-to-facility mapping table

---

## Source 3: Corporate Travel Data

### What was researched
SAP Concur Expense API v3:
- JSON response format
- ExpenseTypeCode: AIRFR (airfare), HOTEL (lodging), GRND (ground transport)
- SegmentData contains departure and arrival location codes for flights
- TransactionAmount, TransactionCurrencyCode, VendorName, BusinessPurpose

Navan (formerly TripActions) export format:
- trip_id, traveler_name, traveler_email
- origin_iata, destination_iata (IATA airport codes)
- departure_date, arrival_date, cabin_class
- booking_type: flight, hotel, car
- hotel_name, hotel_city, hotel_country, nights
- distance_km: sometimes provided, often null for flights

Key finding on distances:
Neither Concur nor Navan consistently provides flight distance in kilometers.
They provide IATA airport codes only.
All major travel emission calculators (DEFRA, ICAO, Atmosfair) compute:
airport code → coordinates → great-circle distance → cabin class factor → radiative forcing

### DEFRA 2024 emission factors used
Domestic flights economy: 0.24532 kg CO2e per passenger km
Short haul international economy: 0.15302 kg CO2e per passenger km
Long haul international economy: 0.19085 kg CO2e per passenger km
Business class: multiply by 2.0 (seat takes more space)
First class: multiply by 4.0
Radiative forcing index: 1.891 applied to all flights (contrails and NOx at altitude)
Hotel stay: 20.8 kg CO2e per room night (DEFRA accommodation factor)
Taxi and ride-share: 0.14930 kg CO2e per km
Rail UK average: 0.03549 kg CO2e per passenger km

### What our sample data looks like and why
File: sample_travel_data.json
Format: JSON array of trip objects, modeled on Navan export format
Contents:
- TRIP-001: BOM to LHR business class return (tests long haul business class factor)
- TRIP-001: 6 night London hotel (tests hotel emission calculation)
- TRIP-002: DEL to BOM economy return (tests short haul economy factor)
- TRIP-003: BOM to JFK economy return (tests long haul economy factor)
- Ground transport: taxis and rail in each trip (tests ground transport factors)
- Mixed cities: Mumbai, London, Delhi, New York (realistic enterprise travel)

Airport coordinate lookup table covers 500 major airports including:
BOM, DEL, LHR, JFK, DXB, SIN, HKG, CDG, FRA, SYD, LAX, ORD, NRT, BLR, HYD, MAA

### What would break in real deployment
- Airport code coverage: full IATA database has 10000 airports, we cover 500
- Private and regional airports not in lookup table default to 800km estimate
- Hotel emission factors should vary by location grid mix
- Radiative forcing index is contested: GHG Protocol Scope 3 uses CO2 only, DEFRA uses 1.891
- Traveler-level reporting needs privacy controls on traveler email field
- Currency normalization needed if tracking travel spend alongside emissions