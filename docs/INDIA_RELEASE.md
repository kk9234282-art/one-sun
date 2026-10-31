# All-India company master: release ingestion and online snapshot

Source: the repository owner's public [india-data-v1 release](https://github.com/kk9234282-art/one-sun/releases/tag/india-data-v1), asset `company_master_data_2026-10-31.zip`.

- Downloaded ZIP: **216,238,578 bytes**.
- SHA-256 verified against GitHub's published release digest: `b6dfedff66c92f5eeff0caf5ea0b493c3cba00f6695413bd6a1c1b80fe0979dc`.
- Five CSV files; expanded total **1,043,430,058 bytes**. ZIP CRCs were checked while reading.
- Source rows: **3,236,964**.
- Accepted distinct company CINs: **3,236,908**.
- Rejected rows: **56** (55 malformed CINs; one negative paid-up capital).
- Duplicate valid CINs: **0**.

No rejected identifier or capital value was guessed or repaired. Original rejected rows are retained in the data branch's `deployment/national/exceptions.csv`, downloadable from the website's Data & imports panel. The raw release remains available for independent reprocessing. The date label comes from the filename; official publisher, source authenticity and national completeness have not been independently verified.

An additional **2,291 accepted companies have implausible source incorporation dates**: 2,289 contain `1111-11-11`, one contains `5600-02-01`, and one contains `9076-08-29`. Their identities and other master information remain available. These original dates are retained and flagged in profiles but withheld from date filters, incorporation trends and business-history scores; no corrected date is inferred from the CIN. Country/company counts are unchanged. The catalog records this reversible analysis policy separately from the immutable source chunks.

## Accepted-record statistics

| Measure | Records |
|---|---:|
| Imported companies | 3,236,908 |
| Active | 2,189,416 |
| Defined inactive/closed statuses | 1,005,971 |
| Other statuses | 41,521 |
| Private, including OPC | 3,082,357 |
| Public | 154,551 |
| Marked Listed in supplied data | 9,439 |
| Marked Unlisted in supplied data | 3,227,469 |
| Imported financial statements | 0 |

These categories are different views of the same companies, not additive market totals. Listing labels are from the master data, not independently reconciled exchange securities. LLP and MSME registrations were not supplied and remain separate empty imported universes.

The records cover 36 canonical state/UT labels. Known aliases are documented in `source-report.json`, including Orissa → Odisha and Pondicherry → Puducherry. The historic Dadra & Nagar Haveli and Daman and Diu labels are grouped under their combined current UT. Original source labels are retained in full profiles. Case differences are normalized. No district, NIC code or financial metric is inferred from a CIN/address. State coverage is not independently exhaustive; for example, the source includes only four Sikkim records.

The CIN validator now checks the 21-character structure with a three-letter constitution segment rather than an incomplete code allowlist. Additional source codes such as PLN and GAT are retained; source company class is preserved rather than guessed from those codes. Identifier structure alone does not authenticate registration.

## Static hosting and reproducibility

There are **1,697 bounded compressed data chunks**, each at most **280,367 bytes**, with SHA-256 descriptors in the main-branch catalog. Global and state name indices, profile buckets, state totals and national totals reconcile to the accepted CIN count. Dataset artifacts total approximately **419 MB**, kept on the separate data branch rather than inside the Vercel site output.

Data commit: `bab28087f778efc69f3c47e2645e001e021b4ed3` on `data/india-index-v1`. Main pins this immutable commit and does not merge its data tree. The browser verifies each fetched chunk before decompression/use. Public GitHub raw responses were checked for CORS and matching payload hashes. The Vercel bundle contains the UI, national catalog and source report only, under 1 MB, with no paid data service.

Rebuild pipeline, after obtaining and checksum-verifying the exact source release:

```sh
.venv/bin/python scripts/build_online_india.py
.venv/bin/python scripts/augment_online_facets.py
.venv/bin/python scripts/apply_date_quality.py
.venv/bin/python scripts/prepare_data_branch.py
.venv/bin/python scripts/render_online_site.py
node scripts/build-preview.mjs
```

`build_online_india.py` uses a separate ignored SQLite build cache; it does not replace the private Flask database or publish accounts/history/keys. Data snapshots use versioned branches and a reviewed source digest. The preparation script refuses to overwrite an existing differing versioned data branch. For a new release, review the digest/version and use a new cache/version instead of silently reusing the old build. No source archives are downloaded during the Vercel website build.

The hosted search is a read-only snapshot. Full-country substring searches can transfer multiple index chunks; state filters narrow this. Non-name sorting supports the first 50,000 matching rows; deeper pagination should use name sorting or narrower filters. CSV exports contain directory/index fields and are capped at 50,000 matches. Full original master fields, including addresses and source-state labels, are available in profiles and the original release. Missing financials stay unknown, and the research indicator is not a SEBI eligibility test or investment recommendation.
