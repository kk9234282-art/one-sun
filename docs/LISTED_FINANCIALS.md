# Listed-company financial statements

## Current data status

The supplied company master contains registration, listing labels and capital fields. A separate **real NSE financial overlay now contains 2,236 annual statements for 1,198 exactly matched company CINs**. Of these, 1,192 companies have standalone statements and 1,026 have consolidated statements. There are 2,218 statements for FY ending 2026 and 18 for FY ending 2025; latest source publication is 2026-10-30. This is partial coverage of the 9,439 master records labelled listed, not a claim to cover every exchange-listed issuer.

On 2026-11-01, publishing the environment configuration activated the saved NSE/BSE domains. NSE's public results page, advertised CSV downloads and linked archive XBRL files became accessible. BSE's public results page returned its own HTTP 403; no bypass was attempted. No paid data service or API subscription was added.

NSE's current reports are under the public **Integrated Filing – Financials** section. The older annual-results page returned mostly delayed historic filings and was not used to label those as current results. The importer downloaded issuer-declared CIN/symbol/ISIN from publicly linked BRSR files, matched exact CINs to the master, and checked symbols/ISIN against financial XBRL. Symbol case was normalized; typos or conflicting identifiers were not guessed. One issuer's invalid placeholder CIN remained unmatched. No company-name matching was used.

2,376 candidate filings were processed; 2,236 parsed into supported annual statements. The coverage report lists excluded nonannual/unsupported contexts, mismatched identifiers and unavailable source files. Four workers, caches, verified TLS and stop-on-401/403/429 rules were used. Only the site's advertised exports and public archive links were read, not authenticated or challenge-protected interfaces. Raw BRSR/filing XML remains in the ignored local build cache; no employee/contact data from those reports is published.

The complete coverage and exception summary is in `deployment/national/financial-source-report.json`, also copied to `/national/financial-source-report.json` in the site build. The data-only financial branch is `data/listed-financials-v3`, pinned by immutable URL and SHA-256 in the national catalog. Synthetic fixtures remain confined to tests.

Listed-company figures show **Not imported** where no statement exists for the requested year/basis, and **Not reported** where an imported statement omits a metric. Public availability of other filings does not mean they have been matched/imported here. Banking total income is labelled separately from revenue from operations. The company master and its listing labels are otherwise unchanged.

## Input and validation

Use the header-only template at `intelligence/static/listed-financials-template.csv`. Supply an authorised real financial export, including an exact CIN, annual period end, 12-month duration, FY-end year, standalone/consolidated basis, units, source URL and actual source publication date. Financial-year year must agree with the period-end year. NSE/BSE source IDs must reference their official HTTPS domains. Company-report references are accepted as explicitly supplied sources, without implying independent verification. Source files do not authenticate their own provenance merely by naming an exchange.

All CINs must exist in the exact listed subset of this master snapshot. Names, PINs and paid-up capital are never used to infer financial values or company identity. The NSE adapter uses an issuer-declared symbol/ISIN/CIN cross-reference, not symbol-to-name guessing. Quarterly/TTM data, future dates, unknown units, non-finite amounts, invalid dates and missing references are rejected. A missing value remains null; zero and negative profit remain real values. Conflicting same-date records block publication. Later source publications can replace an earlier statement for the same CIN/year/basis. The source CSV hash is recorded; the original export should be retained by its operator.

## Prepare and publish a real dataset

From the repository root:

```bash
.venv/bin/python scripts/build_listed_financials.py /path/to/real-financial-export.csv
```

Review `instance/build/listed-financials/validation-report.json`. Any rejected rows prevent dataset preparation. No records are sent to a network service. With a clean report and real data:

```bash
.venv/bin/python scripts/prepare_financial_branch.py --branch data/listed-financials-v4
```

This creates a reviewable, immutable data-only Git branch and pins its URL/checksum in `deployment/national/catalog.json`; it does not push or deploy automatically. Publish the prepared data branch and main catalog through the repository's normal deployment process. Use a new versioned branch for subsequent changes. The publisher checks the validation report, source snapshot and content hash. The build validates immutable data URLs and source-snapshot compatibility. Company data and account databases remain separate.

## Application behavior

The national worker verifies the financial pack's checksum and source snapshot, then joins by exact CIN. It selects the requested reporting basis and FY, or the latest imported annual year for that basis. It never silently falls back between standalone and consolidated accounts. Financial figures in the directory and CSV are converted to INR; profiles retain source units, period end, year, reporting basis, publication date and statement links.

Annual growth uses the immediately preceding year with the same basis and fiscal period end, converting each year's units independently. Growth remains missing across gaps or changed period ends. Profit growth is not calculated from zero/negative prior profit. Selected financials feed the existing evidence-score rules; compliance and industry prospects remain unassessed.

Revenue/profit filters, sorts, overview coverage and exports use the selected figures. Financial filters use the small listed-company index rather than scanning the whole master. Uncovered listed companies keep blank financials. The existing public site remains functional when no financial descriptor is present.

Validation: `pytest`, `node tests/test_financials.mjs`, `node tests/test_online_worker.mjs`, and the listed-company browser smoke test. The financial tests use temporary or in-memory fixtures only.

## NSE acquisition and financial definitions

The public exports used were the integrated-financial-filing and BRSR CSV downloads linked by NSE's company-filings page, restricted to submissions from 2026-04-01 through 2026-10-31. Export request parameters were read from that page's own download binding; this is not advertised as a general supported third-party API. Recheck the public page before refreshing exports if its format changes.

`scripts/fetch_nse_identity.py` caches and extracts issuer-declared identity facts. `scripts/fetch_nse_financials.py` selects the latest exchange-publication timestamp per symbol/basis/reporting-period candidate, parses exact annual contexts through `intelligence/nse_financials.py`, and validates each record. `scripts/audit_nse_financials.py` writes the aggregate coverage report. The original normalized source CSV and detailed fetch report remain under `instance/build/nse-financials/`; their hashes are retained in published metadata. The scripts do not publish automatically.

Only dimensionless 12-month contexts are accepted. Quarterly, half-year and segment figures are excluded. Source XBRL units must represent INR; the `decimals` and rounding labels describe precision, not multipliers. Operations revenue is retained when reported. For NSE banking-format files, reported total income is accepted only with the corresponding income/interest facts and is identified as `total_income_banking`. There are 40 such banking statements in the current overlay. The directory uses **Revenue / income** and provides a metric tooltip; CSV exports preserve `revenue_metric`. Profit is the reported profit/loss for the period, not EPS, operating profit, or an estimate.

Annual growth is withheld when the revenue definition changes between years. Missing figures, balance-sheet totals that are not explicitly reported and EBITDA that is not explicitly reported remain null. Most imported companies have only one annual year here, so prior-year growth cannot be assumed.
