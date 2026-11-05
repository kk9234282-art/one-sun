# Match explanations and manual reviews

Company results now have a lazy **Why this matches** explanation. It uses the filters that actually produced those results, including CIN code, reference edition and exact/broad precision, ambiguous candidates, source-description identity confidence, geography and screening criteria. Changing a form field without applying it does not change an existing result's explanation. A registered-industry difference is not presented as proof of an error or two current businesses.

Open a company profile and choose **Open saved review / add a review** to load or write a manual review. A review requires a description, activity tags, source link, supporting excerpt, review date, source type and identity-check method. Source publication date is optional. The reviewer explicitly chooses whether the finding is manually reviewed or still needs checking. A name-only match remains labelled identity unconfirmed.

## Storage scope

- **Public static Vercel website:** reviews are private to the current browser and origin, using IndexedDB. They survive normal reloads, but are not shared, synced or backed up. Clearing site data, browser profiles or the site origin can make them unavailable. The UI states this beside the editor and review list. Saving does not send a network request.
- **Authenticated Flask application:** reviews are saved to the application SQLite database, shared among signed-in analysts/admins. Existing session authentication and CSRF protection apply. Public static hosting does not expose this API or database. Shared public/cross-device reviews require deploying and connecting a writable authenticated backend; none has been added to the static hosting setup.

Every edit creates a new revision. Previous revisions stay stored, including the source and identity claim. Saving against an outdated version fails rather than overwriting a newer review. The authenticated API returns at most 20 revisions per company, and the list returns at most 200 companies. The browser list reads at most 200 latest entries. Original records, imported descriptions, financials, automated filter results and evidence scores remain separate from manual review assessments.

The **Reviewed activities** button opens the saved-company list. No download/export controls were added.

## Free-resource limits

No new paid service, database subscription, background crawler, scheduler, analytics request or company-dataset asset is introduced. The small research script is served with the existing static assets. Explanations are constructed only when expanded and use loaded records. Reviews/history are loaded only after the user opens them. Static reviews use the visitor's browser storage; the optional Flask writes are short SQLite transactions with optimistic version checks, indexed queries and a 64 KiB request limit.

## Authenticated API

- `GET /api/activity-reviews`: up to 200 latest reviewed companies.
- `GET /api/company/<cin>/activity-reviews`: current review and latest 20 revisions.
- `POST /api/company/<cin>/activity-reviews`: append a revision with `expected_version`, the source fields and existing session CSRF header. A stale expected version returns HTTP 409.

A manual review records the reviewer's assessment. It does not independently authenticate the website, source claim or current operations, and is never promoted into verified financial evidence.
