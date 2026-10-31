"""Official endpoints only. Discovery URLs are not represented as verified APIs."""
import csv
import io
import os
import re
from urllib.parse import urlparse
import requests

SOURCES = {
 'user_upload': {'name': 'User-supplied datasets', 'url': '', 'mode': 'upload',
                 'note': 'Uploaded records retained with file checksums and declared coverage. Original publisher and publication date are not independently verified.'},
 'mca': {'name': 'Ministry of Corporate Affairs', 'url': 'https://www.mca.gov.in/', 'mode': 'manual',
         'note': 'Import permitted company/LLP master downloads. No public unauthenticated API is assumed.'},
 'mca_cdm': {'name': 'MCA Corporate Data Management', 'url': 'https://mcacdm.nic.in/', 'mode': 'manual',
             'note': 'Official portal discovery; access and downloadable formats must be verified by the operator.'},
 'data_gov': {'name': 'Open Government Data — company master', 'url': 'https://data.gov.in/catalog/company-master-data', 'mode': 'api',
              'note': 'Set DATA_GOV_RESOURCE_ID from the selected resource’s API documentation and DATA_GOV_API_KEY. Catalog URL is not an API resource ID.'},
 'nse': {'name': 'National Stock Exchange', 'url': 'https://www.nseindia.com/', 'mode': 'csv',
         'download': 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv',
         'note': 'Equity security list; contains ISIN and symbol, usually no CIN. Do not infer company identity from names.'},
 'bse': {'name': 'BSE', 'url': 'https://www.bseindia.com/', 'mode': 'manual',
         'note': 'Import permitted List of Securities downloads. No undocumented or authenticated API is scraped.'},
 'udyam': {'name': 'Udyam Registration', 'url': 'https://udyamregistration.gov.in/', 'mode': 'manual',
           'note': 'Import authorised registration-level exports only. No public bulk registration API verified.'},
 'msme_dashboard': {'name': 'MSME Dashboard', 'url': 'https://dashboard.msme.gov.in/', 'mode': 'manual',
                    'note': 'Aggregate dashboard data cannot be imported as registration-level records or summed with companies.'},
}


class SourceError(ValueError):
    pass


def session():
    s = requests.Session()
    s.headers['User-Agent'] = 'IndiaCorporateIntelligence/1.0 (official public data research)'
    # Use the platform's trusted CA bundle; never turn verification off.
    s.verify = os.getenv('REQUESTS_CA_BUNDLE', '/etc/ssl/certs/ca-certificates.crt')
    return s


def download_nse(target):
    url = SOURCES['nse']['download']
    with session().get(url, stream=True, timeout=(10, 60), allow_redirects=False) as r:
        r.raise_for_status()
        if r.status_code != 200:
            raise SourceError('Unexpected redirect/status; inspect official download manually.')
        size = 0
        with open(target, 'wb') as output:
            for chunk in r.iter_content(65536):
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    raise SourceError('Download exceeds 100 MiB limit')
                output.write(chunk)
    with open(target, encoding='utf-8-sig') as f:
        headers = next(csv.reader(f), [])
    if 'SYMBOL' not in headers or not any('ISIN' in h for h in headers):
        raise SourceError('Official endpoint did not return the expected NSE CSV schema')
    return url


def download_data_gov(target, offset=0, max_pages=100):
    resource = os.getenv('DATA_GOV_RESOURCE_ID', '')
    key = os.getenv('DATA_GOV_API_KEY', '')
    if not re.fullmatch(r'[a-zA-Z0-9-]+', resource) or not key:
        raise SourceError('Configure DATA_GOV_RESOURCE_ID and DATA_GOV_API_KEY from official resource documentation')
    url = f'https://api.data.gov.in/resource/{resource}'
    # Each page is materialized separately; bounded memory and resumable offset.
    count = 0
    with session() as s, open(target, 'w', newline='', encoding='utf-8') as output:
        writer = None
        for _ in range(max_pages):
            response = s.get(url, params={'api-key': key, 'format': 'json', 'offset': offset, 'limit': 1000},
                             timeout=(10, 60), allow_redirects=False)
            if response.status_code != 200:
                # Never include response.request.url: the API key is in its query string.
                raise SourceError(f'OGD returned HTTP {response.status_code}')
            data = response.json()
            rows = data.get('records')
            if not isinstance(rows, list):
                raise SourceError('OGD response has no records array')
            if not rows:
                break
            if writer is None:
                writer = csv.DictWriter(output, fieldnames=list(rows[0]), extrasaction='raise')
                writer.writeheader()
            writer.writerows(rows)
            count += len(rows)
            offset += len(rows)
            if str(data.get('total','')).isdigit() and offset >= int(data['total']):
                break
            if len(rows) < 1000:
                break
        else:
            raise SourceError(f'Page budget reached; no import performed. Re-run with a larger --max-pages or chunk using --offset {offset}.')
    if not count:
        raise SourceError('OGD returned no records; verify resource ID and offset')
    return url, offset


def probe(source_id):
    source = SOURCES[source_id]
    if source['mode'] == 'upload':
        return 'local', 'Local file imports; no remote availability or publisher verification is implied'
    try:
        with session().get(source.get('download', source['url']), stream=True,
                           timeout=(8, 20), allow_redirects=False) as r:
            if r.status_code == 200:
                return 'reachable', 'HTTP 200; dataset schema and terms still require verification'
            return 'blocked', f'HTTP {r.status_code}; no access-control bypass attempted'
    except requests.RequestException:
        return 'unavailable', 'Network/TLS/proxy request failed; credentials and response details were not logged'
