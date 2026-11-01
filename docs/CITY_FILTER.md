# PIN-based districts and city / postal areas

Choose a state, then a **District**, **City / postal area**, an exact six-digit **PIN code**, or a combination. Hover over or focus the asterisks for mapping explanations. ROC is not shown as a dashboard filter.

The company list and profile show the PIN-derived district and representative city/postal area. The original company-file district is preserved separately as `source_district`, even when blank. Matching fills the displayed district from the PIN reference; it does not infer from addresses or ROC. Unresolved locations display **Not identified**.

The dashboard shows counts for every matching district within the selected state. Choose or click a district to see every matching city/postal-area count, including unidentified areas. Click an area to filter the company list. Scroll the geographic charts to see all entries; these charts are not limited to the top 14. Counts describe unique company CINs, not operating businesses or official city censuses.

For example, PIN 413102 maps to Pune district and the representative postal area Baramati; PIN 421401 maps to Thane district and Murbad. A PIN can cover multiple places, so these area labels are not verified municipal city locations. The third-party source's `village` label is retained only when unambiguous within that state/PIN and the district is known. Conflicting or missing labels remain unidentified. Dashboard counts, listed rows and CSV exports use the same enrichment and filters.

No registered address is parsed. The district lookup uses only the source company PIN and state, joined to the bundled postal reference. ROC filters the source registrar field independently; a registrar jurisdiction can cover several cities and is never used as a company-city fallback.

Postal districts are not municipal boundaries: for example, PIN 421401 maps to Thane district. A district selection may include neighbouring towns. Missing, invalid, ambiguous and state-mismatched PIN mappings remain **Not identified**. Those companies can still be filtered by their source PIN. No address or ROC fallback supplies a missing district.

The current snapshot maps 2,682,629 companies and leaves 554,279 unidentified, totaling 3,236,908. District labels follow the reference and are not guaranteed current municipal names.

## Postal reference

Bundled from `india-pincode@2.5.9` (Deepak Kumar, MIT), published 2026-03-16. The underlying postal-record date is unspecified. Source and SHA-512 package integrity are recorded in `intelligence/static/pin-districts.json`; see [third-party notice](THIRD_PARTY_POSTAL.md). This is a third-party reference, not a live India Post verification. No paid API, runtime third-party calls or credentials are required.

`scripts/build_pin_reference.py` verifies the pinned package, reads only its JSON, and retains a state/PIN pair only when all valid office rows agree on one district. It does not install or execute package code. State aliases are documented in `intelligence/locality.py`.

`scripts/build_city_index.py` builds compact `[district ID, ROC ID, source PIN]` sidecars aligned to immutable national state indices. SHA-256 and ordered CIN checksums protect the join. `scripts/prepare_city_branch.py` publishes a separate data-only branch and pins its commit in the main catalog. The original company data commit stays unchanged. Bulk sidecars load on demand and stay out of the Vercel website build.

The same lookup runs in Flask, local CSV mode and local ZIP mode. Saved local ZIP databases do not require reimporting.


## Rebuild the geographic metadata

After `scripts/build_pin_reference.py`, run `scripts/build_postal_areas.py` to add separately attributed area labels. Then run `scripts/build_geography.py` to add CIN-aligned national PIN sidecars and reconciled geographic counts to each state descriptor. `--reuse-global` reuses existing global PIN sidecars when only the area reference changes. Run `scripts/prepare_city_branch.py` to pin a new versioned data-only branch; never overwrite a published data commit. The global PIN sidecar lets even the unfiltered first page show geographic details without downloading all profiles. The original national company index commit and record count stay unchanged.
