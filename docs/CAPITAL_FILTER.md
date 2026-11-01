# Paid-up capital ranges

The main filter dropdown and clickable paid-up capital chart use the same non-overlapping ranges:

- Below ₹1 crore: known values below ₹10,000,000, including zero.
- ₹1 crore to below ₹10 crore: ₹10,000,000 inclusive to ₹100,000,000 exclusive.
- ₹10 crore and above: ₹100,000,000 inclusive.
- Unknown capital: missing values only. Zero is a known value.

All capital ranges clears this selection. The filter combines with state, district, postal area, PIN and the other controls. The advanced minimum-capital field remains available for custom lower bounds and intersects with a selected range.

The same filter applies to company rows, dashboard counts, research screening and CSV exports in the national static site, Flask, local CSV and local ZIP modes.

`scripts/augment_capital_facets.py` builds national capital-range summaries from the immutable index and applies the existing date-quality flags. Counts reconcile with the published capital chart and total record count. Existing company data and geographic sidecars are unchanged; cached summaries keep basic range browsing fast. Unknown capital may have zero matching records in a supplied snapshot.
