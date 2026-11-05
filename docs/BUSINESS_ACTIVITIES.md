# Business activity research

The master has 20 broad industrial categories. Its normalized `nic` field is empty across 3,236,908 records. Five-digit activity codes are preserved from CIN positions 2–6, but the source does not declare a classification version. The application does not assign a guessed NIC edition or relabel the registered industry. A separate [bulk CIN reference lookup](CIN_ACTIVITIES.md) now preserves version-labelled candidates across the full master, including explicit broad and ambiguous matches.

The first enrichment batch extracts 1,143 public About descriptions from already cached Screener issuer pages. It now provides 47 overlapping research-topic tags after the version-2 rules update. Leading legal company names do not supply tag evidence, and selected plantation/customer-use phrases are excluded from downstream product tags. These tags describe the source text, may overlap, and are research aids rather than an independently verified taxonomy. Company names do not determine tags.

- **CIN-checked match (255):** earlier annual-report research established the target CIN and issuer symbol. The cached page must match its saved SHA-256 and NSE symbol. The identity evidence link is retained. This checks the entity match, not the accuracy or currentness of the description.
- **Name-match lead (888):** earlier unique normalized legal-name matching and page NSE-symbol checks discovered a candidate. The master CIN is not confirmed. These descriptions stay visibly unverified and can be excluded with the evidence filter.
- **Needs research:** no imported business description. This does not mean the company has no business or no public information.

The company profile keeps registered industry, exact CIN code, source-described operations, activity tags, retrieval date, source URL and identity evidence separate. The activity filters do not modify financial statements or research scores. Text searches are literal case-insensitive substrings of descriptions. Tag/evidence/text filters can be combined with the existing geography, capital and listing filters. Searches with a positive description criterion use the bounded enrichment index rather than downloading the full national dataset.

## Rebuild and expand

Run `.venv/bin/python scripts/build_business_activities.py` from the repository root. This is an offline rebuild of cached sources, not a new web search. It checks saved page checksums and symbol identity, rejects missing descriptions, then writes a deterministic compressed asset, manifest and audit report. The build checks the asset checksum and source snapshot before deployment. Original source records are preserved.

A separate local queue at `instance/reports/business-activity-next-1000.json` prioritizes the largest paid-up-capital companies without imported descriptions. It is pending research, not completed research. Future collection should acquire permitted public company/annual-report descriptions, retain retrieval date, content checksum and source URL, check CIN identity, and avoid replacing conflicting descriptions without review. Newly acquired evidence must be explicitly added to the builder; no background crawler is running.

The published enrichment applies to the shared master. Locally opened CSV/ZIP files have not been enriched; activity filters reject those modes explicitly instead of silently producing misleading results.

The version-2 update changes tag sets for 236 of the 1,143 descriptions while preserving every description, master field, source URL/hash and identity confidence field. It adds wood/plywood, poultry/eggs, aquaculture/seafood, feed, agricultural-input/seed, fashion-accessory, lubricant/petroleum-product, investment/holding and unspecified-alcohol topics. Generic alcohol is not classified as confirmed alcoholic beverages. These remain research aids, not verified current operating roles.
