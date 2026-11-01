# Official source investigation

Update — 1 November 2026: the published environment now permits the requested official domains. NSE public CSV/XBRL downloads work; 2,236 supported annual statements for 1,198 exactly matched CINs were imported. BSE returned its own HTTP 403 and was not bypassed. See [financial coverage and acquisition details](LISTED_FINANCIALS.md) and the published financial-source report. The earlier blocked-access investigation below is historical.

Checked in this cloud task on 31 October 2026. No credentials were requested or extracted. The environment initially permits package-manager/Git destinations only. Direct HEAD requests to the NSE CSV and OGD catalog returned proxy `CONNECT 403`. All seven in-application reachability checks failed through the configured proxy. This establishes an environment access blocker, **not** that the official services are down. The domains have been saved as an additive configuration draft and have not been demonstrated to work in the current runtime.

| Source | Official URL / candidate endpoint | Integration | Verified here |
|---|---|---|---|
| MCA | https://www.mca.gov.in/ | Authorised company/LLP, statement, director and filing CSV/XLSX import | No remote access; manual adapter tested |
| MCA CDM | https://mcacdm.nic.in/ | Permitted company/LLP export import | No remote access; manual adapter tested |
| OGD company master | https://data.gov.in/catalog/company-master-data | Resource-specific API and CSV/XLSX; candidate REST pattern `https://api.data.gov.in/resource/{resource-id}` | API resource ID and live schema not verified |
| NSE | https://www.nseindia.com/ ; candidate current-equity download https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv | Bounded streaming CSV, header validation, NSE adapter | Proxy denied; live endpoint/schema not verified |
| BSE | https://www.bseindia.com/ | Authorised securities/financial/filing export adapter | No live endpoint verified; no undocumented API used |
| Udyam | https://udyamregistration.gov.in/ | Authorised registration-level export adapter | No public bulk API verified |
| MSME dashboard | https://dashboard.msme.gov.in/ | Reachability monitor / source discovery only | No live dataset verified; aggregate counts intentionally rejected as entity records |

Each source has its own capability declaration, mapping constraints, source status and audit identity. MCA, CDM, BSE and Udyam are manual connector paths sharing validated import machinery; they are not advertised as automatic live API integrations. Portal accessibility alone would not establish permission to scrape or redistribute data. No CAPTCHA, cookie challenge, authentication or rate-limit workaround is implemented.

## Enable live checks

Review/save the added domains in environment settings, then publish/apply the environment configuration as supported by the product. Added custom domains: `www.mca.gov.in`, `mcacdm.nic.in`, `data.gov.in`, `api.data.gov.in`, `www.nseindia.com`, `nsearchives.nseindia.com`, `archives.nseindia.com`, `www.bseindia.com`, `api.bseindia.com`, `udyamregistration.gov.in`, `dashboard.msme.gov.in`. Existing package-manager presets remain intact. Runtime access must be retried; draft persistence does not enable connectivity.

For OGD, locate the desired resource under the official catalog and read its current API documentation. Configure `DATA_GOV_RESOURCE_ID` and `DATA_GOV_API_KEY` securely in runtime environment settings, with the key scoped to `api.data.gov.in`. No concrete API resource is assumed from the catalog URL. The connector uses limit/offset pagination, fixed HTTPS host, timeouts, normal certificate verification and no redirects. It never logs API-key-bearing URLs. Resource publication date and schema must be checked before importing. Other domains might be required by actual permitted downloads; add them only after inspecting the official link.

Start with a small, dated official company-master export. Import it, check audit counts and rejected rows, verify a sample of CIN/name/source references against the official source, then expand to remaining states and dates. Financial records generally require separate authorised filings; absence of free financial coverage must stay visible. Exchange security data without an authorised CIN mapping remains separate from company coverage. No national coverage or real-data verification can be claimed until this process succeeds.

Screener supplemental financial coverage was added on 2026-11-01: 402 annual statements for 202 previously uncovered Active listed CINs, verified using NSE annual-report PDFs. Public table rounding, report dates and table retrieval dates are retained. The run stopped on HTTP 429 and deferred 724 candidates; no bypass or immediate retry was attempted. See `deployment/national/screener-source-report.json` for counts and exclusions.

A subsequent normalized-name batch verified another 53 Active listed CINs (106 annual statements) from 120 candidates. Existing financial data was preserved. Combined coverage is now 1,453 companies; the batch audit is `deployment/national/screener-name-source-report.json`. Name variants discover candidates only; import still requires exact CIN evidence.

Unverified web-revenue research is a separate dataset for 31,994 Active companies with paid-up capital ≥ ₹10 crore. Existing statement coverage includes 1,352 of these companies. Cached public annual tables supplied 150 additional name-only revenue leads after deduplicating one share-class alias; 30,492 companies remain unresearched. This did not perform a general internet search. Each lead is low confidence and retains source, period, source company name and observed date. These figures never enter financial-statement filters, growth or scores. The full target CSV includes generated manual search links, which are not source evidence.
