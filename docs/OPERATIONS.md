# Architecture and operations

## Runtime

Flask 3 / Gunicorn, server-rendered Jinja templates, local vanilla JavaScript/CSS, SQLite WAL and openpyxl. This keeps deployment costs and setup low, avoids external chart/CDN dependencies and permits a fully functional offline research workspace. SQL relationships and normalized company/financial/security tables provide a migration path, but the current queries use SQLite syntax; PostgreSQL migration is an engineering task, not a drop-in environment variable.

The web application uses a single persistent SQLite database per deployment. Two Gunicorn workers with two threads each are a reasonable initial configuration. Ingestion serializes writers; larger national datasets should be loaded by CLI in controlled batches, not concurrent browser uploads. CSV exports stream; Excel exports are bounded to 100,000 rows. API pagination is bounded. Dashboard aggregation scans the selected company universe and should be benchmarked on real imported volumes; materialized aggregates are not yet implemented.

## Security and deployment

Run `create-user` in the deployment environment; no signup/default account exists. Analysts have read/export access; only administrators can import or probe sources. Passwords are scrypt hashes. Session IDs rotate on login, writes require CSRF tokens and login failures are throttled per directly observed remote IP. If deploying behind a proxy, explicitly design trusted forwarded-IP handling; the app deliberately does not trust arbitrary `X-Forwarded-For`. Expired attempts are reset on the next attempt. This is a single-node rate limiter, not distributed abuse protection.

Set a long random `SECRET_KEY`, preserve it outside source control and use `COOKIE_SECURE=1` behind a TLS reverse proxy. The local fallback key is generated with mode 0600 under `instance/session.key`. User passwords, API keys and this file must never be committed. Protect the database volume and backups, restrict administrative access and apply your data-retention obligations. Do not import director personal data without authorisation. No cookie/CAPTCHA bypass or general user-supplied remote URL fetch exists. All network connectors use fixed official hosts and TLS verification.

Example container commands (provided for deployment; not built or verified in this cloud task):

```sh
docker build -t atlas-india .
docker volume create atlas-data
docker run --rm -it -v atlas-data:/app/instance atlas-india flask --app wsgi create-user admin
# Supply SECRET_KEY securely via the deployment secret manager; do not paste it into source.
docker run --rm --env-file /secure/atlas.env -v atlas-data:/app/instance -p 8000:8000 atlas-india
```

The image runs as nonroot. Ensure the mounted volume is writable by the image user before startup. TLS termination, domain routing, ingress authentication policy, vulnerability scanning, container verification and real-data load tests remain deployment responsibilities. Flask's development server is for local use only. `/healthz` checks database accessibility and does not prove official-source health or coverage.

## Repeatable maintenance

Dependencies: create/reuse `.venv`, then `pip install -r requirements.txt`. All application data is under ignored `instance/` unless `DATABASE_PATH` overrides it. Startup does not need network calls or database seeding. Each cloud task is already isolated; use the existing checkout and do not create Git worktrees unless explicitly requested.

After access and source terms/schema have been verified, schedule the CLI `sync` command in the host scheduler with the actual source publication date. OGD exposes `--offset` and `--max-pages`; page budget exhaustion aborts without import, so use smaller resource chunks or increase the budget explicitly. A rerun of an identical import is idempotent. Endpoint sync is an operator command, not an always-running background scheduler. Catch-up requires current source metadata, not blindly using today's date.

Use SQLite's online backup API, not a live copy of only the main file while WAL writes are active. Example:

```python
import sqlite3
with sqlite3.connect('instance/intelligence.sqlite') as source:
    with sqlite3.connect('/secure/backups/intelligence.sqlite') as target:
        source.backup(target)
```

Test restoration in a separate deployment, including users, record histories, source metadata and file permissions. This task has not validated a production backup/restore or public deployment. Keep raw source artifacts plus checksums in a controlled external archive; uploaded temporary files are removed after import.

## Scale beyond an initial research deployment

For concurrent national-scale workloads: migrate schema/queries to PostgreSQL with explicit migrations, introduce durable object storage for raw official artifacts, add a job queue/worker with checkpointed batches, version source schemas, materialize reproducible coverage aggregates and add independent administrative audit retention. Evaluate SSO/MFA, distributed login limiting, monitoring and alerting, recurring refresh SLAs and deployment-specific load tests. These capabilities are not claimed by the current implementation.

The supplied tests verify correctness of the initial implementation and isolated browser interactions. They do not establish official-data completeness, compliance with third-party terms, financial accuracy of an uploaded source or production capacity.
