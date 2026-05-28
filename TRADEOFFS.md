# TRADEOFFS.md — Three Things Deliberately Not Built

## 1. Real SAP API Integration

What we did instead:
Flat file CSV upload matching real SAP MB51 export format.
Same German column headers, same unit inconsistencies, same date formats, same movement types.

Why we did not build it:
Real SAP integration requires one of four mechanisms:
- IDoc: requires SAP PI/PO or Cloud Integration middleware layer
- OData REST API: requires SAP Fiori Gateway with correct authorization objects configured by BASIS team
- BAPI function calls: requires SAP RFC protocol and live system connection
- SAP Integration Suite: enterprise middleware, months of setup

None of this is possible without a live SAP instance.
More importantly it does not change the correctness of the data model,
normalization logic, validation engine, or review workflow.
Those are the actual engineering substance of this system.

The flat file approach tests the entire pipeline correctly.
A sustainability analyst asking the SAP team to export MB51 and upload the CSV
is the most common real-world workflow today.

Production path:
Scheduled pull from SAP OData API endpoint or SFTP drop where SAP pushes flat files.
Parser logic, normalization, validation, staging, review, audit — all unchanged.

What would break in production:
- Plant code lookup table needed to resolve Werk codes to facility names and locations
- Movement type filtering needed to separate consumption from procurement
- Material master lookup needed to resolve material numbers to human readable names
- Decimal separator handling: German locale uses comma not period

## 2. OCR for PDF Utility Bills

What we did instead:
Portal CSV export upload. Same analyst workflow, 100% reliable parsing.

Why we did not build it:
PDF utility bills are the most common format analysts receive but extraction is genuinely hard:
- Bill layouts vary completely per utility: PG&E looks nothing like Tata Power or EON
- Multi-meter consolidated bills have complex table structures
- Scanned paper bills require OCR not just PDF text extraction
- OCR accuracy on numbers is imperfect
- A misread decimal point in consumption changes the emissions calculation significantly
- Some PDFs use image-based rendering even for text, breaking standard text extraction

Building reliable OCR means:
PDF to image rendering, OCR engine (Tesseract or cloud Vision API),
structured field extraction, confidence scoring, human review of low-confidence extractions.
This is a product in itself, not a feature.

Portal CSV is the second most common format.
Most enterprise utility portals offer CSV download.
The upload UX is identical — analyst downloads CSV from portal instead of PDF.

Production path:
PDF ingestion added as parallel upload mode with dedicated extraction service.
Layout detection, confidence scoring, automatic flagging of low-confidence extractions for human review.

What would break in production:
- Half-hourly smart meter data: 48 rows per meter per day, millions of rows annually
- Per-utility grid emission factors by location and year
- Market-based vs location-based Scope 2 accounting

## 3. Kafka and Microservices Architecture

What we did instead:
Synchronous Django processing. File upload triggers parse, normalize, validate, save, return response.
All in one request cycle. Clean, simple, debuggable.

Why we did not build it:
A message queue architecture would mean:
File upload triggers async task, task queued, worker picks it up,
normalizes rows, publishes to validation topic, validation worker processes,
results written to DB, frontend polls for completion.

This is correct for high volume production systems where:
- Uploads contain hundreds of thousands of rows
- Processing takes 30 or more seconds
- Multiple worker instances needed for parallel processing
- Processing failures need retry without re-uploading

For this prototype:
- Expected upload size: hundreds to low thousands of rows
- Processing time: under 5 seconds for typical uploads
- Single instance deployment on Railway
- Adding async workers adds Celery, Redis, worker deployment, task state management
- All for a problem that does not exist at this scale

The architecture is already correct.
We have a clear ingestion step, normalization step, validation step.
Making it async is an operational concern, not an architectural one.
Same functions wrapped in Celery tasks if volume demands it.

Production path:
Add Celery and Redis for async processing when row volumes exceed 10000 per upload.
Job status endpoint the frontend polls.
Processing logic itself unchanged.

## Also Deliberately Not Built

PostgreSQL RLS:
Mentioned as future production enhancement in MODEL.md.
Application-level client_id filtering enforces tenant isolation today.
RLS would enforce at database engine level — even raw SQL cannot cross tenant boundaries.
Not implemented due to prototype scope.

SCD Type 2 versioning:
Considered full historical versioning with active and inactive record rows.
Replaced by AuditLog with complete before_state and after_state JSON snapshots.
Same audit capability, much simpler implementation.

AI anomaly detection:
Basic rule-based validation is sufficient for prototype.
Three rules: negative values, missing fields, 3x spike detection.
AI would add complexity without proportional benefit at this stage.

Real-time dashboard updates:
Frontend polls on navigation, not real-time websocket push.
Sufficient for analyst review workflow where actions are deliberate not continuous.
WebSocket with Django Channels would be production enhancement.

Multi-analyst locking:
No row-level pessimistic locking if two analysts review same row simultaneously.
Acceptable for prototype where analyst teams are small.
Production would add optimistic locking with version numbers.