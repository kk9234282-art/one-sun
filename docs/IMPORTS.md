# Import contract and statistical semantics

CSV must be UTF-8 (BOM allowed). XLSX uses the first sheet, read-only, evaluated values only. Do not upload macros or password-protected documents. Files are temporarily stored then deleted; retain the original official files outside the application in your controlled archive. The audit log records SHA-256, source, publication date, type, inserted/updated/rejected counts and the first 100 row errors. Individual original rows can be tied to import IDs through current and historical records. There is no claim that a source-labelled manual upload has been independently authenticated.

## Required fields

| Kind | Keys and required fields | Sources |
|---|---|---|
| companies | cin, name | mca, mca_cdm, data_gov |
| llps | llpin, name | mca, mca_cdm, data_gov |
| msmes | registration_id, name | udyam |
| securities | exchange, symbol, name, status; optional cin and isin | nse, bse |
| financials | cin, financial_year, reporting_type, unit, source_url | mca, nse, bse |
| directors | cin, din, name, source_url | mca |
| filings | cin, filing_id, kind, filed_on, source_url | mca, nse, bse |

Download templates from the authenticated UI for optional columns. Common MCA/NSE header aliases are normalized in `intelligence/ingest.py`; unsupported schemas require explicit mapping review. Unknown columns are ignored, not interpreted. Duplicate normalized headers reject a file. Dates support ISO, Indian numeric dates and NSE `DD-Mon-YYYY`. CIN requires its 21-character structure; LLPIN and Udyam IDs have separate validation. Structural validation does not prove registration authenticity. Industry labels and NIC codes are retained separately; no guessed sector mapping is applied.

Company class is Private/Public; missing is unknown. Registered status is retained, with exact Active status counted active. Explicit closed/inactive statuses (Strike Off, Struck Off, Dormant, Dissolved, Under Liquidation, Inactive, Amalgamated) are counted separately; other statuses are displayed as other/unknown. These are source statuses, not assessments of operating activity. Future source dates are rejected.

Capital and market capitalization are INR. Financial metrics are in the statement's `unit`: exactly `INR`, `INR lakh`, or `INR crore`. `financial_year` is the year ending (e.g. 2025 for FY2024–25). `reporting_type` is `standalone` or `consolidated`; these are never merged. A financial revision clears omitted metrics to NULL rather than mixing statements/units; previous statement data is archived. Negative profits are valid. Negative capital, assets or liabilities and non-finite numbers are rejected. Source references must use HTTPS.

## Identity and history

Company master identity is CIN; name similarity is never enough for merging. Financial statements/directors/filings must refer to an existing CIN. Import masters first. Securities without a CIN are retained as **unlinked securities**, not manufactured company records. Only an authorised CIN mapping can link them. An ISIN alone identifies a security, not a legal company. Dual NSE/BSE records count once in company statistics when both link to the same CIN.

NSE `EQUITY_L.csv` is treated as a current admitted-equity list: its rows default to `Listed`; supply explicit status when importing historical NSE files. BSE requires explicit status. Only `Listed` or `Active` linked securities establish listed-company evidence. The master can separately declare `listing_status=listed` or `unlisted`. Absence from an exchange file does **not** establish unlisted status. Unknown listings are never passed to the IPO screen. A source disappearance does not automatically delete or delist a record; import a status update with provenance.

LLPs and MSME registrations remain independent tables. Udyam registrations may overlap incorporated companies or LLPs; their counts are never added to a company total. Dashboard LLP/MSME cards describe all imported registrations and do not inherit company filters. The exchange universe is security-level and is not a unique listed-company count. Company filters do not apply to these independent directories; their current UI supports name search and pagination.

Upserts use stable primary keys and publication dates. Older snapshots cannot overwrite newer records. Identical file/source/type/date combinations are logged once and return a duplicate result, including previously rejected batches; correct the file before retrying. Company snapshots and historical names are archived, financial revisions are archived, and updates to all other imported types are saved in `record_history`. `field_sources` preserves source, publication date and import ID per updated field: a partial master update does not falsely relabel omitted fields as newly sourced. The current record's source/date describes its latest contributing import. Original files must be retained externally for full reprocessing.

Each import is a single write transaction. Row validation/foreign-key errors reject that row and permit other valid rows; these imports are `partial`, with nonzero CLI exit status. File-level parse/schema failures roll back imported records and mark the batch `failed`. A zero-row import fails. Readers see only committed state. For million-row sources, split into date-consistent batches and use CLI/off-hours; the current single-file transaction is deliberately conservative and does not promise parallel bulk ingestion.

## Research score

Defaults: revenue growth 25; profitability 20; financial stability 20; business history 15; corporate compliance 10; industry prospects 10. Set `SCORE_WEIGHTS_JSON` to a JSON object with all six snake_case factor names, nonnegative values summing to 100.

- Growth: clip(consecutive-year revenue growth / 25%, 0, 1).
- Profitability: clip(net margin / 15%, 0, 1).
- Stability: clip(1 − liabilities/assets, 0, 1); assets must be positive. This is a narrow balance-sheet indicator, not a solvency opinion.
- History: clip(age in years / 10, 0, 1).
- Compliance and industry prospects: insufficient evidence; not scored. Company Active status does not prove compliance.

Each assessed factor is multiplied by its configured weight. Display observed points and assessable weight; do not divide by assessable weight to present a spurious complete score. A missing financial statement, nonpositive prior-year growth base or omitted factor remains unknown. Score uses latest available selected-basis financials and incorporation age as of the execution date. There is no claim of future IPO prediction. **Not a SEBI IPO eligibility test or investment recommendation.**

Date filters refer to source snapshot dates or incorporation dates, not point-in-time reconstruction of the whole database. Historical snapshots are retained for audit; the current analytics query current records. Explicit FY selection chooses that year only; it does not substitute a nearby available year.
