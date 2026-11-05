# CIN-based registration activity references

All **3,236,908** published companies were processed offline. The exact five-digit activity segment at CIN positions 2–6 is compared with version-labelled NIC 2004 and NIC 2008 references. This is registration-code evidence; it does not establish what the company currently does.

| Result | All companies | Active companies |
| --- | ---: | ---: |
| One reference candidate; company edition unconfirmed | 2,438,264 | 1,708,021 |
| Multiple reference candidates | 683,053 | 439,623 |
| Code meaning unresolved | 115,591 | 41,772 |
| Total processed | 3,236,908 | 2,189,416 |

A candidate is available for **3,121,317** companies, including **2,147,644 Active companies** (98.1% of the Active scope). These counts must not be added to the 1,143 source-described companies as if they were independently researched current businesses.

## Interpretation rules

- A five-digit exact reference match retains its edition and description.
- If there is no exact match in an edition, a code ending in zero can have a four-digit class candidate; a code ending in two zeros can have a three-digit group candidate. These are explicitly marked **broad matches**, never represented as detailed subclass matches.
- Every edition's candidate is preserved. For example, `72200` has a broad NIC 2004 software candidate and an exact NIC 2008 social-sciences R&D candidate. The application does not silently choose either.
- Codes such as `99999` remain unresolved. Company names, incorporation years and the supplied broad industry are not used to invent a classification edition or override a candidate.
- Even one candidate is labelled **edition unconfirmed**. The master does not declare the classification version; other historical editions may differ. Matching a reference is not independent confirmation of the master or current operations.

## Sources

The NIC 2004 detailed-structure PDF is a public mirror of the MOSPI publication, pinned to [this GitHub version](https://github.com/matcdac/CorporateIndiaDataSourceXLSX/blob/cca5f086d19e8337a09641ba8df7fe997d075af7/understanding-metadata/nic_2004_struc_detail.pdf). Its SHA-256 is retained in the bundled reference metadata. The parser preserves code strings and excludes seven alphabetic `(A)` repair subclasses rather than merging them into numeric CIN codes.

The NIC 2008 titles use a [pinned third-party transcription](https://github.com/colaberry/WorldOfTaxonomy/blob/62f31df232fb38a0c2da5dac2068f30dc04d3618/frontend/public/llms-codes/nic_2008.txt), whose documented source is the MOSPI NIC 2008 workbook. It is labelled as a transcription, not an independently authenticated official download. The original MOSPI URLs, mirror URLs and input hashes are included in `intelligence/data/cin-activity-reference.json`.

## Rebuild

`prepare_cin_reference.py` accepts the pinned 2004 PDF plus its `pdftotext -layout` text and the pinned 2008 transcription. It checks input hashes and expected numeric subclass counts before producing the bundled reference. Run it only after obtaining those documented inputs.

Run `.venv/bin/python scripts/build_cin_activities.py` to process the existing national index. Every input chunk is checksum-checked; totals must reconcile to the company catalog. The output is a compressed code dictionary with precomputed all-company and Active statistics, and code-to-index-chunk references. The website build checks the output checksum and source snapshot. No original records or sourced business descriptions are overwritten.

The website adds a searchable **CIN registered activity** dropdown, advanced reference-text/status filters, and a version-labelled registration panel in profiles. These filters work alongside geography, capital, listing and source-description filters. Precomputed counts and chunk references avoid a full national download for ordinary code lookups. Locally opened user CSV/ZIP files are excluded from this published-snapshot enrichment.
