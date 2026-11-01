# Paid-up capital ranges

The main filter dropdown and clickable paid-up capital chart use the same non-overlapping ranges:

- Below ₹1 crore: known values below ₹10,000,000, including zero.
- ₹1 crore to below ₹10 crore: ₹10,000,000 inclusive to ₹100,000,000 exclusive.
- ₹10 crore and above: ₹100,000,000 inclusive.
- Unknown capital: missing values only. Zero is a known value.

All capital ranges clears this selection. The filter combines with state, district, postal area, PIN and the other controls. The advanced minimum-capital field remains available for custom lower bounds and intersects with a selected range.

The same filter applies to company rows, dashboard counts, research screening and CSV exports in the national static site, Flask, local CSV and local ZIP modes.

`scripts/augment_capital_facets.py` builds national capital-range summaries from the immutable index and applies the existing date-quality flags. Counts reconcile with the published capital chart and total record count. Existing company data and geographic sidecars are unchanged; cached summaries keep basic range browsing fast. Unknown capital may have zero matching records in a supplied snapshot.


## Listed-company performance

The national static site uses a compact listed-company index whenever `listing=listed`, including capital, state, district, postal area, name, class, status and sorting combinations. The original implementation recalculated combined-filter totals by reading all 3,236,908 company rows and PIN sidecars.

`scripts/build_listed_index.py` selects only companies explicitly labelled listed in the same immutable source index, then copies their original normalized profile fields from the local build cache. `scripts/prepare_listed_branch.py` publishes the gzip and source/checksum manifest on a separate immutable data branch. The catalog pins the data URL and verifies the source snapshot and field layout. Existing source-date quality rules and geographic enrichment still apply; listing labels are not newly inferred or independently exchange-verified.

This snapshot has 9,439 listed records in a 782,530-byte gzip; 1,576 have known paid-up capital below ₹1 crore. The first search reads this one file. Pagination, sorting, combined filters, overview totals and CSV exports reuse it without reading national company indices, PIN sidecars or profile buckets. Original company counts and data are unchanged. Filters outside the listed universe retain their existing query paths.

Run `node tests/test_online_worker.mjs` for cold-query request-count regressions and `.venv/bin/python tests/listed_filter_browser_smoke.py` for the real-data browser check. The latter verifies the exact result count, range values, pagination, sort order, geographic/class combinations, CSV, one-file data access and mobile layout. Browser timing is measured against local static HTTP and does not guarantee a particular public-network latency.
