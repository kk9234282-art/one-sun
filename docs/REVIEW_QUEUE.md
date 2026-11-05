# Classification review queue

The **Needs review** module focuses on the **439,623 Active companies with multiple CIN reference candidates** in the published snapshot. Multiple candidates can describe similar or different activities; they are not automatically classified as errors. Other unresolved or single-candidate companies remain available in the ordinary directory and are outside this queue.

Each card compares the supplied broad registered industry, version-labelled CIN reference meanings and exact/broad precision, and any available source description. Name-match source leads remain visibly unverified. Opening a company uses the existing profile/review workflow.

## Priority and progress

The default order places the **246 companies with imported source descriptions** first, then sorts by paid-up capital descending. An alternative sorts all queue companies by capital first. Unknown capital is last, and CIN is the stable tie-breaker. An imported description does not mark a manual review complete.

The queue has Pending, Manually reviewed and All views, with 20 companies per page. Progress counts only queue members whose **latest saved review status is `reviewed`**. Changing a review back to `needs_review` returns the company to Pending. Reviews of unrelated, inactive, unresolved or single-candidate companies do not inflate these totals.

Public-site progress is private to reviews saved in the current browser, not a global project total. Clearing site data removes those reviews. The authenticated Flask queue uses shared SQLite review history and its own imported company universe. These scopes are labelled in the interface.

## Keeping free resources small

No paid service, crawler, scheduler or polling loop is introduced. Original national indices are read once offline to build the queue. The published queue assets total about **13 MB**, but browsers do **not** download that dataset in full.

The ordinary catalog gains only one small descriptor. The queue manifest is fetched only when the queue is opened (about 54 KB compressed). The first data file is about 16 KB compressed and supports several 20-row pages. The worker reuses the existing classification/description data and caches loaded chunks. Checked-review membership is verified using small, hashed CIN-to-rank files only for saved review IDs. Unrelated reviews are excluded exactly, without national-index scans. Reads are limited to four concurrent chunks.

The capital sort uses a sparse mapping for the 246 source-described companies instead of publishing a second copy of the queue. Pending pagination skips saved checks mathematically. Only requested page records are loaded. Browser progress is read on queue opening, explicit refresh or a review-save event; it does not run in the background. The browser worker accepts at most 10,000 saved checked CINs per request to bound memory/work.

## Rebuild and validation

Run `.venv/bin/python scripts/build_review_queue.py` after changing the source snapshot or imported business descriptions. It checks original chunk hashes, reconciles queue size with the CIN report, produces deterministic immutable pages/membership files and updates the catalog descriptor/report. Rebuild cleanup removes only stale generated queue files, keeping hosting storage bounded. Manual review changes do not require rebuilding any assets.

The website build validates metadata, snapshot identity, row totals and all queue file hashes, then copies only the small queue asset directory. Full-data browser checks verify source-first/capital sorting, exact progress transitions, reopening saved reviews, mobile layout and no national-index downloads. The initial queue view downloaded under 100 KB; a tested sequence of queue/review interactions and reload stayed under 500 KB of queue-file traffic.
