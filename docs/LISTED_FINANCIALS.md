# Listed-company financial statements

## Current data status

The current financial overlay contains **2,744 annual statements for 1,453 Active listed company CINs**: the original 2,236 NSE statements for 1,198 companies, plus 508 verified Screener statements for 255 previously uncovered companies. There are 1,447 companies with standalone data and 1,026 with consolidated data. Of the 7,441 Active listed records in the master, **5,988 remain uncovered**. This is partial imported coverage, not a claim to cover every currently traded issuer. Latest report/statement dissemination is 2026-10-30; Screener table retrieval is separately recorded as 2026-11-01.

On 2026-11-01, publishing the environment configuration activated the saved NSE/BSE domains. NSE's public results page, advertised CSV downloads and linked archive XBRL files became accessible. BSE's public results page returned its own HTTP 403; no bypass was attempted. No paid data service or API subscription was added.

NSE's current reports are under the public **Integrated Filing – Financials** section. The older annual-results page returned mostly delayed historic filings and was not used to label those as current results. The importer downloaded issuer-declared CIN/symbol/ISIN from publicly linked BRSR files, matched exact CINs to the master, and checked symbols/ISIN against financial XBRL. Symbol case was normalized; typos or conflicting identifiers were not guessed. One issuer's invalid placeholder CIN remained unmatched. No company-name matching was used.

2,376 candidate filings were processed; 2,236 parsed into supported annual statements. The coverage report lists excluded nonannual/unsupported contexts, mismatched identifiers and unavailable source files. Four workers, caches, verified TLS and stop-on-401/403/429 rules were used. Only the site's advertised exports and public archive links were read, not authenticated or challenge-protected interfaces. Raw BRSR/filing XML remains in the ignored local build cache; no employee/contact data from those reports is published.

The original NSE coverage summary is in `deployment/national/financial-source-report.json`; supplemental coverage and exclusions are in `deployment/national/screener-source-report.json`. Both are copied into the site build. The combined data-only financial branch is `data/listed-financials-v5`, pinned by immutable URL and SHA-256 in the national catalog. Synthetic fixtures remain confined to tests.

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
.venv/bin/python scripts/prepare_financial_branch.py --branch data/listed-financials-v5
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


## Supplemental Screener annual tables

`scripts/fetch_screener_financials.py` discovers uncovered **Active listed** candidates from NSE's public equity list. A unique legal name only discovers a candidate: import requires its exact master CIN in the first 20 pages of its NSE-linked annual-report PDF, followed by an exact match between that NSE symbol and Screener's public company page. Public crawling rules are read first. Requests are paced, evidence is cached, progress is checkpointed, and access/rate denials stop new downloads. No search, login, paid export, challenge, or hidden API is used.

Only explicitly labelled standalone annual profit/loss tables in INR crore are accepted. TTM columns, unmatched annual periods, ambiguous reporting bases and missing monetary values are not inferred. At most the matching annual-report year and its comparative year are imported; consecutive matching period ends are required. Displayed crore amounts are converted to INR and labelled as potentially rounded. The source `as_of` is the verified NSE annual-report dissemination date; `source_retrieved_on` records the distinct Screener retrieval date. This does not claim Screener published or refreshed its table on that report date. The statement link points to Screener; a separate identity reference points to the NSE report.

`scripts/merge_screener_financials.py` validates completed fetch results and combines additions with the existing overlay. It refuses to replace any already covered CIN. Build/publish the validated financial pack and then regenerate the Active listed CSV and coverage queue. Raw PDFs are temporary; source checksums and extracted identity evidence remain local. The dashboard profile and CSV retain source, reporting basis, precision and date provenance.

The November 1 Screener run attempted 417 candidates before an HTTP 429 rate-limit response stopped downloads; 724 candidates were deferred. Of the attempted candidates, 202 passed identity, basis and period checks. Remaining candidates had unavailable/unreadable reports, absent CIN evidence, unsupported tables or other recorded exceptions. No rate-limit bypass or automatic retry followed the denial. Future runs use slower pacing.

Name-variant discovery is available with `scripts/fetch_screener_financials.py --name-variants-only`. It expands Ltd/Limited and ignores spacing/punctuation to find unique candidates across the Active listed master. It never treats a name as identity proof: every addition still requires the exact CIN in the linked NSE annual report and the NSE symbol on Screener. The separate checkpoint preserves the earlier exact-name audit. Merge with `scripts/merge_screener_financials.py --report name-variants-fetch-report.json`.

The name-variant batch checked all 120 additional candidates and verified 53 new CINs (106 annual statements). It completed without a rate/access stop. The other 67 candidates remain excluded for missing identity/report evidence, unclear reporting basis or unavailable source files. Its separate audit is `/national/screener-name-source-report.json`.
