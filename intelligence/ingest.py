"""Streaming, auditable upserts. Missing fields never silently erase known values."""
import csv
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from openpyxl import load_workbook
from .db import now

KINDS = {'companies': ('companies', ['cin']), 'llps': ('llps', ['llpin']),
         'msmes': ('msmes', ['registration_id']), 'securities': ('securities', ['exchange', 'symbol']),
         'financials': ('financials', ['cin', 'financial_year', 'reporting_type']),
         'directors': ('directors', ['cin', 'din']), 'filings': ('filings', ['cin', 'filing_id'])}
ALIASES = {
 'company_name': 'name', 'companyname': 'name', 'name_of_company': 'name', 'name_of_the_company': 'name',
 'corporate_identification_number': 'cin', 'company_cin': 'cin', 'company_class': 'class',
 'companyclass': 'class', 'company_category': 'category', 'companycategory': 'category',
 'company_status': 'status', 'companystatus': 'status', 'company_state_code': 'state',
 'date_of_incorporation': 'incorporated', 'dateofincorporation': 'incorporated',
 'registered_office_address': 'address', 'registered_office': 'address',
 'registeredofficeaddress': 'address', 'authorized_capital': 'authorised_capital',
 'authorisedcapital': 'authorised_capital', 'paidup_capital': 'paid_up_capital',
 'paidupcapital': 'paid_up_capital', 'company_industrial_classification': 'nic',
 'principal_business_activity_as_per_cin': 'industry', 'company_roc_code': 'roc',
 'isin_number': 'isin', 'name_of_company': 'name', 'date_of_listing': 'listed_on',
 'security_code': 'symbol', 'scrip_code': 'symbol', 'security_name': 'name',
 'security_id': 'symbol', 'udyam_registration_number': 'registration_id',
 'llp_name': 'name', 'llp_status': 'status', 'llp_incorporation_date': 'incorporated',
 'state_name': 'state', 'net_profit_inr': 'net_profit', 'total_assets': 'assets',
 'total_liabilities': 'liabilities', 'financial_year_end': 'financial_year',
 'company_registration_date': 'incorporated', 'company_address': 'address',
 'company_state': 'state', 'company_roc': 'roc', 'pin_code': 'postal_code',
 'company_sub_category': 'subcategory',
}
NUMBERS = {'authorised_capital', 'paid_up_capital', 'market_cap_inr', 'revenue', 'expenses', 'ebitda', 'net_profit', 'assets', 'liabilities'}
REQUIRED = {'companies': ['cin', 'name'], 'llps': ['llpin', 'name'], 'msmes': ['registration_id', 'name'],
            'securities': ['exchange', 'symbol', 'name'],
            'financials': ['cin', 'financial_year', 'reporting_type', 'unit', 'source_url'],
            'directors': ['cin', 'din', 'name', 'source_url'],
            'filings': ['cin', 'filing_id', 'kind', 'filed_on', 'source_url']}
SOURCE_KINDS = {'mca': {'companies','llps','financials','directors','filings'},
                'mca_cdm': {'companies','llps'}, 'data_gov': {'companies','llps'},
                'nse': {'securities','financials','filings'}, 'bse': {'securities','financials','filings'},
                'udyam': {'msmes'}, 'msme_dashboard': set()}
SOURCE_KINDS['user_upload'] = set(KINDS)
# This export supplies a sector label here, not a numeric NIC classification.
ALIASES['company_industrial_classification'] = 'industry'


def header(value):
    key = re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')
    return ALIASES.get(key, key)


def records(path):
    if Path(path).suffix.lower() == '.xlsx':
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            rows = book.active.iter_rows(values_only=True)
            names = [header(c) for c in next(rows)]
            if len(names) != len(set(names)):
                raise ValueError('Duplicate normalized headers')
            for row in rows:
                if any(v is not None for v in row):
                    yield dict(zip(names, row))
        finally:
            book.close()
    else:
        with open(path, encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError('CSV header required')
            names = [header(c) for c in reader.fieldnames]
            if len(names) != len(set(names)):
                raise ValueError('Duplicate normalized headers')
            for row in reader:
                if None in row:
                    raise ValueError('CSV row has more values than headers')
                yield {header(k): v for k, v in row.items()}


def iso_date(value):
    if isinstance(value, (datetime, date)):
        return value.strftime('%Y-%m-%d')
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y', '%d-%b-%y'):
        try:
            return datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError('Invalid date; use YYYY-MM-DD')


def normalize(raw, kind, source):
    values = {k: v.strip() if isinstance(v, str) else v for k, v in raw.items()}
    values = {k: v for k, v in values.items() if v not in (None, '', 'NA', 'N/A', 'null', '-')}
    if kind == 'securities':
        values.setdefault('exchange', source.upper())
        # NSE EQUITY_L is a current admitted-equity list. Other files must state status.
        if source == 'nse':
            values.setdefault('status', 'Listed')
        if 'status' not in values:
            raise ValueError('Security status is required')
    for key in REQUIRED[kind]:
        if key not in values:
            raise ValueError(f'Missing {key}')
    for key in ('cin', 'llpin', 'isin', 'exchange', 'registration_id'):
        if key in values:
            values[key] = str(values[key]).upper()
    if 'cin' in values and not re.fullmatch(r'[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}', values['cin']):
        raise ValueError('Invalid CIN')
    if kind == 'llps' and not re.fullmatch(r'[A-Z]{3}-\d{4}', values['llpin']):
        raise ValueError('Invalid LLPIN')
    if kind == 'msmes' and not re.fullmatch(r'UDYAM-[A-Z]{2}-\d{2}-\d{7}', values['registration_id']):
        raise ValueError('Invalid Udyam registration ID')
    if 'isin' in values and not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d', values['isin']):
        raise ValueError('Invalid ISIN format')
    for key in ('incorporated', 'listed_on', 'filed_on', 'appointed_on', 'ceased_on'):
        if key in values:
            values[key] = iso_date(values[key])
    for key in NUMBERS.intersection(values):
        import math
        values[key] = float(str(values[key]).replace(',', ''))
        if not math.isfinite(values[key]):
            raise ValueError(f'Non-finite {key}')
        if key in {'authorised_capital','paid_up_capital','market_cap_inr','assets','liabilities'} and values[key] < 0:
            raise ValueError(f'Negative {key}')
    if 'class' in values:
        values.setdefault('registered_class', values['class'])
        classes = {'private': 'Private', 'public': 'Public', 'private limited': 'Private', 'public limited': 'Public', 'one person company': 'Private'}
        values['class'] = classes.get(str(values['class']).lower(), values['class'])
        if values['class'] not in ('Private','Public'):
            raise ValueError('Company class must be Private or Public')
    if 'status' in values:
        values['status'] = str(values['status']).strip().title()
    if 'state' in values:
        values['state'] = str(values['state']).title()
    if 'listing_status' in values:
        values['listing_status'] = str(values['listing_status']).lower()
        if values['listing_status'] not in ('listed','unlisted'):
            raise ValueError('Listing status must be listed or unlisted; blank means unknown')
    if kind == 'financials':
        values['financial_year'] = int(values['financial_year'])
        if not 1900 <= values['financial_year'] <= date.today().year + 1:
            raise ValueError('Invalid financial year end')
        if values['unit'] not in ('INR','INR lakh','INR crore'):
            raise ValueError('Unit must be INR, INR lakh or INR crore')
        if values['reporting_type'] not in ('standalone','consolidated'):
            raise ValueError('Invalid reporting type')
    if 'source_url' in values and not str(values['source_url']).startswith('https://'):
        raise ValueError('An HTTPS source reference is required')
    return values


def ingest(db, path, kind, source, as_of):
    if kind not in KINDS or source not in SOURCE_KINDS or kind not in SOURCE_KINDS[source]:
        raise ValueError('Source does not support this record category')
    as_of = iso_date(as_of)
    if as_of > date.today().isoformat():
        raise ValueError('Source date cannot be in the future')
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            digest.update(chunk)
    checksum = digest.hexdigest()
    old = db.execute('SELECT * FROM imports WHERE source_id=? AND kind=? AND checksum=? AND as_of=?',
                     (source, kind, checksum, as_of)).fetchone()
    if old:
        return dict(old) | {'duplicate': True}
    batch = db.execute('INSERT INTO imports(source_id,kind,filename,checksum,as_of,started_at,status) VALUES(?,?,?,?,?,?,?)',
                       (source,kind,Path(path).name,checksum,as_of,now(),'running')).lastrowid
    db.commit()
    inserted = updated = rejected = 0
    errors = []
    table, keys = KINDS[kind]
    columns = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
    try:
        # Keep per-row savepoints inside a file transaction; releasing an outermost
        # SAVEPOINT would otherwise commit each row and defeat file-level rollback.
        db.execute('BEGIN')
        for line, raw in enumerate(records(path), 2):
            db.execute('SAVEPOINT row_import')
            try:
                row = normalize(raw, kind, source)
                row = {k: v for k, v in row.items() if k in columns}
                row.update(source_id=source, as_of=as_of, import_id=batch)
                if kind == 'companies':
                    row['updated_at'] = now()
                match = ' AND '.join(f'{k}=?' for k in keys)
                previous = db.execute(f'SELECT * FROM {table} WHERE {match}', [row[k] for k in keys]).fetchone()
                if previous and previous['as_of'] > as_of:
                    raise ValueError('Older snapshot cannot replace a newer record')
                if previous and kind == 'financials':
                    # Financial metrics are a coherent statement; never mix omitted values from a revision.
                    for key in NUMBERS.intersection(columns):
                        row.setdefault(key, None)
                    db.execute('INSERT INTO financial_history(cin,financial_year,reporting_type,snapshot,import_id) VALUES(?,?,?,?,?)',
                               (row['cin'],row['financial_year'],row['reporting_type'],json.dumps(dict(previous)),batch))
                if previous and kind == 'companies' and previous['name'] != row['name']:
                    db.execute('INSERT OR IGNORE INTO historical_names VALUES(?,?,?,?)',
                               (row['cin'],previous['name'],previous['as_of'],previous['source_id']))
                if previous and kind not in ('companies','financials'):
                    db.execute('INSERT INTO record_history(kind,record_key,snapshot,import_id) VALUES(?,?,?,?)',
                               (kind,json.dumps([row[k] for k in keys]),json.dumps(dict(previous)),batch))
                fields = list(row)
                assignments = ','.join(f'{k}=excluded.{k}' for k in fields if k not in keys)
                sql = f'INSERT INTO {table}({",".join(fields)}) VALUES({",".join("?" for _ in fields)}) ON CONFLICT({",".join(keys)}) DO UPDATE SET {assignments}'
                db.execute(sql, list(row.values()))
                record_key = json.dumps([row[k] for k in keys])
                for field in row:
                    if field not in {'source_id','as_of','import_id','updated_at'} and field not in keys:
                        db.execute('INSERT INTO field_sources VALUES(?,?,?,?,?,?) ON CONFLICT(kind,record_key,field) DO UPDATE SET source_id=excluded.source_id,as_of=excluded.as_of,import_id=excluded.import_id',
                                   (kind,record_key,field,source,as_of,batch))
                if kind == 'companies':
                    snapshot = dict(db.execute('SELECT * FROM companies WHERE cin=?',(row['cin'],)).fetchone())
                    db.execute('INSERT INTO company_history(cin,import_id,as_of,snapshot) VALUES(?,?,?,?)',
                               (row['cin'],batch,as_of,json.dumps(snapshot)))
                if previous:
                    updated += 1
                else:
                    inserted += 1
                db.execute('RELEASE row_import')
            except (ValueError, TypeError, OverflowError, __import__('sqlite3').IntegrityError) as e:
                db.execute('ROLLBACK TO row_import')
                db.execute('RELEASE row_import')
                rejected += 1
                if len(errors) < 100:
                    errors.append({'line': line, 'error': str(e)})
            # One transaction per file: readers see only committed imports, never half a batch.
        status = 'partial' if rejected else 'completed'
        if not inserted and not updated:
            status = 'failed'
    except Exception as e:
        db.rollback()
        inserted = updated = 0
        status = 'failed'
        errors.append({'error': type(e).__name__ + ': invalid file or schema'})
    db.execute('UPDATE imports SET finished_at=?,status=?,inserted=?,updated=?,rejected=?,errors=? WHERE id=?',
               (now(),status,inserted,updated,rejected,json.dumps(errors),batch))
    db.commit()
    return dict(db.execute('SELECT * FROM imports WHERE id=?',(batch,)).fetchone())
