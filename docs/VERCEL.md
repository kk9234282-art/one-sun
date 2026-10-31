# Free shared national dashboard

## Deploy

Deploy `main` from `kk9234282-art/one-sun` in the existing Vercel project. Root Directory: repository root; Framework: Other; build `node scripts/build-preview.mjs`; output `public`; no install command, Python runtime, secrets or database connection is needed. Redeploy the latest main commit if automatic Git deployments are not enabled.

The current website uses the shared release-derived national catalog. Visitors do not upload or select local files to browse. Country/state/industry summaries, name-sorted pagination and individual profiles fetch small data chunks only when required. Broad searches and complex filters run in a worker and display progress; changing views cancels superseded searches. A state filter reduces data transfer. No paid service was configured.

## Code and data are separate

- `main`: application code, rendered national HTML, small catalog and source report.
- `data/india-index-v1`: immutable compressed indices/profiles and source exceptions. **Do not merge this branch into main or deploy it as the website.** Its root configuration disables Vercel Git deployment.
- Original ZIP: GitHub Release `india-data-v1`, not a website build dependency.

The main catalog pins data commit `bab28087f778efc69f3c47e2645e001e021b4ed3`. The browser fetches hashed chunks from GitHub raw URLs with CORS and verifies SHA-256 before decompressing. The Vercel output stays under 1 MB rather than bundling the approximately 419 MB data tree. Source counts, rejected rows, aliases and limitations are recorded in [INDIA_RELEASE.md](INDIA_RELEASE.md).

Free-plan eligibility, storage/traffic/rate limits and availability remain provider constraints. This is suitable for a periodically refreshed research snapshot, not a guarantee of unlimited hosting or a production SLA. Git LFS, paid database/serverless queries and new paid plans are not used. Keep versioned data history bounded as the project grows; do not blindly accumulate snapshots beyond repository limits.

## Shared browser features

Search by current name/CIN, categorical/date/capital filters, pagination, private/public and listed/unlisted views, charts, state exploration, company profiles and research evidence display operate on the shared snapshot. Known class/status/listing and country/state/industry summaries are precomputed. Other filters scan compact indices in bounded memory, with a small LRU cache. Profile addresses/source fields fetch a single bucket. Regional aliases retain the original state label in profiles.

Missing financial statements remain unknown and fail numeric financial thresholds. There is no live exchange reconciliation, revenue/profit invention or SEBI eligibility determination. Company master listing labels do not create securities records; LLPs and MSMEs are separate unsupplied universes. Historical revisions, authentication and new shared imports still require the full Flask workflow.

Name-sorted pagination can reach all indexed records. Other sorts retain at most the first 50,000 matches for bounded browser memory; use name sort or narrower filters for deeper pagination. CSV downloads include directory/index columns for at most 50,000 matching records. Original full master fields are visible in profiles or the source ZIP. The source panel links to source metadata and all 56 original exception rows.

## Local tools remain separate

The local CSV loader and disk-backed all-India ZIP loader remain available. These views do not upload or add records to the shared national snapshot. **Use published data** restores the online view. A saved local ZIP uses IndexedDB and can be reopened after refresh; records saved using the earlier CIN allowlist should be reimported to apply the current structural policy. Browser storage is not a backup. Encrypted/multi-volume/ZIP64 archives remain unsupported. See README for the local workflow and its disk limits.

## Verification

```sh
node scripts/build-preview.mjs
node tests/test_online_worker.mjs
.venv/bin/python tests/online_national_browser_smoke.py
.venv/bin/python -m pytest -q
```

The national test serves the actual release-derived chunks over static HTTP and checks totals, the small first-page fetch, 36 state/UT labels, pagination, Maharashtra/name filtering, full profile fields, original state preservation, filtered CSV, source exceptions and mobile layout. GitHub-hosted chunk HTTP/CORS/checksum verification was also performed. A local build or source push is not proof that the user's hosted Vercel deployment has completed; that remains the Vercel project's deployment operation.
