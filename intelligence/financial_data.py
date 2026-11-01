"""Validate annual, CIN-linked financial exports before public static publication."""
import csv,hashlib,json,math,re
from datetime import date
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

FIELDS=('revenue','expenses','ebitda','net_profit','assets','liabilities')
REQUIRED={'cin','financial_year','reporting_type','unit','period_end','period_months','source_id','source_url','as_of'}
UNITS={'INR':1,'INR lakh':100000,'INR crore':10000000}

def normalize(raw,listed_cins,today=None):
    today=today or date.today()
    if raw.get(None):raise ValueError('CSV row has more values than headers')
    row={str(k).strip():str(v if v is not None else '').strip() for k,v in raw.items() if k is not None}
    cin=row.get('cin','').upper()
    if not re.fullmatch(r'[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}',cin) or cin not in listed_cins:raise ValueError('CIN is not an exact listed-company match in the master snapshot')
    end=date.fromisoformat(row['period_end']);published=date.fromisoformat(row['as_of']);year=int(row['financial_year'])
    if str(row['period_months'])!='12' or year!=end.year or not 1900<=year<=today.year:raise ValueError('Require an annual 12-month period and matching financial-year end')
    if not end<=published<=today:raise ValueError('Publication date must be on/after period end and not in the future')
    basis=row['reporting_type'].lower();unit=row['unit']
    if basis not in ('standalone','consolidated') or unit not in UNITS:raise ValueError('Specify standalone/consolidated and INR/INR lakh/INR crore')
    url=urlsplit(row['source_url']);source=row['source_id'].lower()
    if url.scheme!='https' or not url.hostname or url.username or url.password or source not in ('nse','bse','company_report','user_upload'):raise ValueError('Require an HTTPS statement reference and declared source')
    if source in ('nse','bse') and not (url.hostname==source+'india.com' or url.hostname.endswith('.'+source+'india.com')):raise ValueError('Exchange source must reference its official domain')
    result={'cin':cin,'financial_year':year,'reporting_type':basis,'unit':unit,'period_end':end.isoformat(),'period_months':12,'source_id':source,'source_url':row['source_url'],'as_of':published.isoformat()}
    for field in FIELDS:
        text=row.get(field,'')
        if text.lower() in ('','na','n/a','null','unknown','-'):result[field]=None;continue
        try:value=Decimal(text.replace(',',''))
        except InvalidOperation:raise ValueError(f'{field} is not a number') from None
        if not value.is_finite() or not math.isfinite(float(value*UNITS[unit])):raise ValueError(f'{field} must be finite')
        if field in ('assets','liabilities') and value<0:raise ValueError(f'{field} cannot be negative')
        result[field]=float(value)
    if result['revenue'] is None and result['net_profit'] is None:raise ValueError('Require revenue or net profit; absent values are not zero')
    return result

def build(path,listed_cins,today=None):
    path=Path(path);selected={};rejected=[];accepted=0
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if not REQUIRED<=set(reader.fieldnames or []):raise ValueError('Missing columns: '+', '.join(sorted(REQUIRED-set(reader.fieldnames or []))))
        if len(reader.fieldnames)!=len(set(reader.fieldnames)):raise ValueError('Duplicate CSV headers')
        for number,raw in enumerate(reader,2):
            try:row=normalize(raw,listed_cins,today)
            except (ValueError,KeyError) as error:rejected.append({'line':number,'reason':str(error)});continue
            key=(row['cin'],row['financial_year'],row['reporting_type']);previous=selected.get(key)
            if previous and previous['period_end']!=row['period_end']:raise ValueError('Conflicting annual period ends for the same CIN/year/basis')
            if previous and previous['as_of']==row['as_of'] and previous!=row:raise ValueError('Conflicting statements with the same CIN/year/basis/publication date')
            if not previous or row['as_of']>previous['as_of']:selected[key]=row
            accepted+=1
    records=sorted(selected.values(),key=lambda row:(row['cin'],row['reporting_type'],-row['financial_year']))
    report={'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'accepted_rows':accepted,'rejected_rows':len(rejected),'reconciled_statements':len(records),'covered_companies':len({row['cin'] for row in records}),'exceptions':rejected}
    return records,report
