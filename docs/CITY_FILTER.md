# City / locality filter

Choose a state, then type or select a city/locality. The dashboard and filtered CSV use the same selection. Reset clears both fields. Existing directory columns remain unchanged.

The supplied master files have no separate city field. Labels come only from an address ending in `locality,district,state,PIN[-India]`, where the state and six-digit PIN agree with the source fields. Ambiguous or unstructured addresses remain **Not identified**. These are address-derived locality labels, not independently verified cities; neighbourhoods and spelling variants remain separate. No city is inferred from ROC or a postal-code lookup.

The current snapshot contains 2,570,166 identified localities and 666,742 unidentified records, totaling 3,236,908 companies. Counts describe records, not distinct cities.

`scripts/build_city_index.py` builds compact integer sidecars from the existing local build cache. Each sidecar is aligned to an immutable state index and verified by SHA-256 and ordered CIN checksum. `scripts/prepare_city_branch.py` publishes a separate data-only Git branch and pins its commit in the main catalog. The original company data commit stays unchanged. Bulk sidecars are excluded from the Vercel website output and load only when needed.

The same conservative extraction runs in Flask, local CSV mode and local ZIP mode; saved local ZIP databases do not require reimporting.
