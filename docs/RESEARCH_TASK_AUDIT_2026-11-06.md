# Research task audit — 6 November 2026

Tested the current national dataset in Chromium against the production build. Browser requests were served from local mirrors of the pinned data; no external research, live-site latency measurement or new primary-source verification was performed. The initial bounded search loaded common reference packs before timing each task. Timings below exclude real GitHub network latency.

## Results

| Research task (Active companies) | Matching records | Check |
| --- | ---: | --- |
| Maharashtra, CIN activity 20110, paid-up capital ≥ ₹10 crore | 2 | Count and first-page CINs reconciled against the saved master records |
| Maharashtra, paid-up capital ≥ ₹10 crore | 8,100 | Count, first two pages and chart totals reconciled against the saved master records |
| Maharashtra, source-described Chemicals, capital ≥ ₹10 crore | 17 | Independently reconciled against the description pack; all 17 descriptions inspected for chemical-related language |
| Maharashtra, listed, latest available standalone revenue ≥ ₹100 crore and positive net profit | 402 | Independently reconciled against the listed master and latest standalone imported statements, with unit conversion |
| Maharashtra, activity 20110, capital ≥ ₹10 crore, description missing | 2 | Missing descriptions remained empty and evidence remained Needs research |

The source-described Chemicals set includes manufacturing, trading and mixed businesses. Standard Industries describes trading in chemicals; it must not be presented as a verified chemical manufacturer. Four matches have prior CIN-checked identity evidence; thirteen remain name-match leads. These identity labels do not verify current operations. Code 20110 uses a broad NIC 2008 reference match and is not a complete chemical-industry census.

The real geography workflow tested a Pune source-described Chemicals search, including a valid empty result, recovery to the 17-company state list, clearing district/city/PIN when changing state, profile research links and a 390-pixel mobile layout. All checks passed.

## Performance issue fixed

Filtered pagination repeated a full state scan after the UI advanced its view generation. It downloaded approximately 16.27 MB again for the next page. The worker now retains at most three completed name-ascending search previews, each limited to the first 100 rows plus exact aggregate statistics. Changed filters, sort, reporting basis and financial year have separate keys; initializing a snapshot clears previews. Later pages outside the preview continue through the normal query path. Basic state/industry/class/status, capital and exact-code filters now reject rows before building full evidence-rich objects.

| Measured task | First page before → after | Next page before → after | Next-page compressed data before → after |
| --- | ---: | ---: | ---: |
| chemicals_capital | 9441 ms → 4578 ms | 8947 ms → 3 ms | 16,265,619 bytes → 0 bytes |
| capital_discovery | 9997 ms → 3934 ms | 10109 ms → 2 ms | 16,265,619 bytes → 0 bytes |

The 20110 task has only two results, so its next-page check is an empty-page boundary test. The 8,100-result task checks normal pagination. Initial complex state searches still read about 16 MB of existing indices; this change reduces repeat work rather than eliminating that first read. No data files, paid services, background jobs or persistent browser storage were added.

## Validation and repeatability

122 Python tests, the online-worker regression suite, the static production build and real-data Chromium workflows passed. Regression checks cover next/empty-page reuse across view generations, changed capital/sort, snapshot invalidation and existing financial/evidence/geography behaviour.

With existing local dataset/cache files, Chromium and Playwright installed:

```sh
node scripts/build-preview.mjs
.venv/bin/python scripts/audit_research_tasks.py
```

The harness writes raw measurements and samples under `work/research-audit/`. It requires the saved `instance/india-online.sqlite` master cache and existing listed/financial mirror files. Results reflect the saved snapshot, not an independently verified national census.

## Remaining priorities

- Preserve the distinction between registration candidates, source descriptions and verified current operations.
- Research business roles for the 17 chemical leads before calling them manufacturers.
- Expand primary-source descriptions and financial coverage selectively; missing statements remain unknown.
- If first-load state scans become a problem on real connections, measure that separately before adding more indices.
