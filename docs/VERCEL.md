# Vercel deployment

This repository deploys a self-contained static dashboard design preview on Vercel. The complete Flask application source remains in the repository for local or persistent-server deployment.

## Deploy from GitHub

1. In Vercel, choose Add New → Project and import `kk9234282-art/one-sun`.
2. Keep Root Directory at the repository root. Framework Preset is **Other** (specified by `framework: null`).
3. Use the repository configuration: build `node scripts/build-preview.mjs`, output directory `public`, no installation command. No environment variables are required.
4. Deploy. Open the HTTPS address provided by Vercel.

The preview has embedded CSS and no company records, aggregate dataset statistics, dataset reports or screenshots. Metrics display Unknown because no data is bundled; these are not zero-company statistics. Navigation links scroll to sections. It is marked read-only and does not pretend to provide live search or imports.

## Local build verification

```sh
node scripts/build-preview.mjs
```

This writes `public/index.html` without Python dependencies or a database. It works in a clean checkout because `preview.html` is committed. The generated `public/` directory is ignored. No Flask function or server is launched by the Vercel configuration.

## Full application hosting

The current Flask application uses a persistent SQLite database. Vercel function filesystems do not provide durable shared SQLite storage, so running this application unchanged as a Vercel function would lose updates or fail on filesystem writes. We intentionally deploy the snapshot rather than advertise a working full backend there.

For the full application now, use a persistent server/container with a protected database volume, following `docs/OPERATIONS.md`. To host the full application on Vercel, first migrate to a durable hosted database and durable file/object storage, adapt the serverless entry point and authentication provisioning, and test imports and concurrency. Those changes are not part of this static deployment and have not been verified.

## What is published

Application source, tests, generic documentation, Vercel configuration and the code-only HTML design preview. User-uploaded files and all data-bearing artifacts stay local and are excluded. The current commit history is also checked to exclude the previously prepared private preview. Local `instance/`, database backups, passwords, session keys, the virtual environment and `.env` files remain ignored.

The export script defaults to a data-free preview. An explicitly requested `--include-data` export writes only to ignored `instance/previews/dashboard.html`. The Vercel build refuses previews lacking the code-only publication marker.

An actual Vercel deployment is performed through your Vercel account after importing the GitHub repository.
