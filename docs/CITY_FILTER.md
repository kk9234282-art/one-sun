# PIN-based district, PIN code and ROC filters

Choose a state, then use **City / district (PIN)**, an exact six-digit **PIN code**, **ROC**, or a combination. Dashboard totals, rows and CSV exports use the same filters. Changing state clears these three fields. Existing hidden directory columns stay hidden.

No registered address is parsed. The district lookup uses only the source company PIN and state, joined to the bundled postal reference. ROC filters the source registrar field independently; a registrar jurisdiction can cover several cities and is never used as a company-city fallback.

Postal districts are not municipal boundaries: for example, PIN 421401 maps to Thane district. A district selection may include neighbouring towns. Missing, invalid, ambiguous and state-mismatched PIN mappings remain **Not identified**. Those companies can still be filtered by their source PIN or ROC. No address or ROC fallback supplies a missing district.

The current snapshot maps 2,682,629 companies and leaves 554,279 unidentified, totaling 3,236,908. District labels follow the reference and are not guaranteed current municipal names.

## Postal reference

Bundled from `india-pincode@2.5.9` (Deepak Kumar, MIT), published 2026-03-16. The underlying postal-record date is unspecified. Source and SHA-512 package integrity are recorded in `intelligence/static/pin-districts.json`; see [third-party notice](THIRD_PARTY_POSTAL.md). This is a third-party reference, not a live India Post verification. No paid API, runtime third-party calls or credentials are required.

`scripts/build_pin_reference.py` verifies the pinned package, reads only its JSON, and retains a state/PIN pair only when all valid office rows agree on one district. It does not install or execute package code. State aliases are documented in `intelligence/locality.py`.

`scripts/build_city_index.py` builds compact `[district ID, ROC ID, source PIN]` sidecars aligned to immutable national state indices. SHA-256 and ordered CIN checksums protect the join. `scripts/prepare_city_branch.py` publishes a separate data-only branch and pins its commit in the main catalog. The original company data commit stays unchanged. Bulk sidecars load on demand and stay out of the Vercel website build.

The same lookup runs in Flask, local CSV mode and local ZIP mode. Saved local ZIP databases do not require reimporting.
