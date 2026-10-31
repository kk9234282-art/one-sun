PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, mode TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'unverified', checked_at TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS imports (
 id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), kind TEXT NOT NULL,
 filename TEXT NOT NULL, checksum TEXT NOT NULL, as_of TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, status TEXT NOT NULL, inserted INTEGER DEFAULT 0, updated INTEGER DEFAULT 0,
 rejected INTEGER DEFAULT 0, errors TEXT NOT NULL DEFAULT '[]', UNIQUE(source_id,kind,checksum,as_of)
);
CREATE TABLE IF NOT EXISTS companies (
 cin TEXT PRIMARY KEY CHECK(length(cin)=21), name TEXT NOT NULL, class TEXT, category TEXT,
 status TEXT, incorporated TEXT, address TEXT, state TEXT, district TEXT, industry TEXT, nic TEXT,
 authorised_capital REAL CHECK(authorised_capital>=0), paid_up_capital REAL CHECK(paid_up_capital>=0),
 listing_status TEXT CHECK(listing_status IN ('listed','unlisted') OR listing_status IS NULL),
 source_id TEXT NOT NULL REFERENCES sources(id), as_of TEXT NOT NULL, updated_at TEXT NOT NULL,
 import_id INTEGER NOT NULL REFERENCES imports(id)
);
CREATE INDEX IF NOT EXISTS company_name_idx ON companies(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS company_state_idx ON companies(state,class,status);
CREATE INDEX IF NOT EXISTS company_industry_idx ON companies(nic,industry);
CREATE INDEX IF NOT EXISTS company_date_idx ON companies(incorporated);
CREATE TABLE IF NOT EXISTS company_history (
 id INTEGER PRIMARY KEY, cin TEXT NOT NULL REFERENCES companies(cin), import_id INTEGER NOT NULL REFERENCES imports(id),
 as_of TEXT NOT NULL, snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historical_names (
 cin TEXT NOT NULL REFERENCES companies(cin), name TEXT NOT NULL, as_of TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES sources(id), PRIMARY KEY(cin,name)
);
CREATE TABLE IF NOT EXISTS llps (
 llpin TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT, state TEXT, incorporated TEXT,
 source_id TEXT NOT NULL REFERENCES sources(id), as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id)
);
CREATE TABLE IF NOT EXISTS msmes (
 registration_id TEXT PRIMARY KEY, name TEXT NOT NULL, state TEXT, category TEXT,
 source_id TEXT NOT NULL REFERENCES sources(id), as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id)
);
CREATE TABLE IF NOT EXISTS securities (
 exchange TEXT NOT NULL CHECK(exchange IN ('NSE','BSE')), symbol TEXT NOT NULL, name TEXT NOT NULL,
 isin TEXT, cin TEXT REFERENCES companies(cin), status TEXT, industry TEXT, listed_on TEXT,
 market_cap_inr REAL CHECK(market_cap_inr>=0), source_id TEXT NOT NULL REFERENCES sources(id),
 as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id), PRIMARY KEY(exchange,symbol)
);
CREATE INDEX IF NOT EXISTS securities_cin_idx ON securities(cin);
CREATE INDEX IF NOT EXISTS securities_isin_idx ON securities(isin);
CREATE TABLE IF NOT EXISTS financials (
 cin TEXT NOT NULL REFERENCES companies(cin), financial_year INTEGER NOT NULL,
 reporting_type TEXT NOT NULL CHECK(reporting_type IN ('standalone','consolidated')),
 unit TEXT NOT NULL CHECK(unit IN ('INR','INR lakh','INR crore')), revenue REAL, expenses REAL, ebitda REAL,
 net_profit REAL, assets REAL, liabilities REAL, source_id TEXT NOT NULL REFERENCES sources(id),
 source_url TEXT NOT NULL, as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id),
 PRIMARY KEY(cin,financial_year,reporting_type)
);
CREATE TABLE IF NOT EXISTS financial_history (
 id INTEGER PRIMARY KEY, cin TEXT NOT NULL REFERENCES companies(cin), financial_year INTEGER NOT NULL,
 reporting_type TEXT NOT NULL, snapshot TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id)
);
CREATE TABLE IF NOT EXISTS directors (
 cin TEXT NOT NULL REFERENCES companies(cin), din TEXT NOT NULL, name TEXT NOT NULL,
 appointed_on TEXT, ceased_on TEXT, source_url TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(id),
 as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id), PRIMARY KEY(cin,din)
);
CREATE TABLE IF NOT EXISTS filings (
 cin TEXT NOT NULL REFERENCES companies(cin), filing_id TEXT NOT NULL, kind TEXT NOT NULL,
 filed_on TEXT NOT NULL, source_url TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES sources(id),
 as_of TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id), PRIMARY KEY(cin,filing_id)
);
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','analyst')), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_start REAL NOT NULL);
CREATE TABLE IF NOT EXISTS record_history (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, record_key TEXT NOT NULL,
 snapshot TEXT NOT NULL, import_id INTEGER NOT NULL REFERENCES imports(id)
);
CREATE INDEX IF NOT EXISTS record_history_key_idx ON record_history(kind,record_key);
CREATE TABLE IF NOT EXISTS field_sources (
 kind TEXT NOT NULL, record_key TEXT NOT NULL, field TEXT NOT NULL,
 source_id TEXT NOT NULL REFERENCES sources(id), as_of TEXT NOT NULL,
 import_id INTEGER NOT NULL REFERENCES imports(id), PRIMARY KEY(kind,record_key,field)
);
CREATE TABLE IF NOT EXISTS import_annotations (
 import_id INTEGER PRIMARY KEY REFERENCES imports(id), title TEXT NOT NULL,
 scope TEXT NOT NULL, date_basis TEXT NOT NULL, provenance TEXT NOT NULL,
 original_sha256 TEXT NOT NULL, archived_file TEXT NOT NULL
);
