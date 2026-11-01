"""Conservative parser for public NSE integrated XBRL annual contexts."""
from datetime import date,timedelta
from decimal import Decimal,InvalidOperation
import re
import xml.etree.ElementTree as ET
NS='{http://www.xbrl.org/2003/instance}'
NIL='{http://www.w3.org/2001/XMLSchema-instance}nil'

def local(tag):return tag.split('}')[-1]
def xml_root(body):
    if len(body)>15*1024*1024 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise ValueError('Oversized/external-entity XML rejected')
    return ET.fromstring(body)
def facts(root):
    result={}
    for element in root:
        if 'contextRef' in element.attrib:result.setdefault((local(element.tag),element.get('contextRef')),[]).append(element)
    return result
def unique_text(elements):
    values={(element.text or '').strip() for element in elements if element.get(NIL) not in ('true','1') and (element.text or '').strip()}
    if len(values)>1:raise ValueError('Conflicting XBRL fact values')
    return next(iter(values),None)
def identity(body):
    root=xml_root(body);records={}
    for element in root:
        name=local(element.tag)
        if name in ('CorporateIdentityNumber','NSESymbol','ISIN'):records.setdefault(name,[]).append(element)
    result={name:(unique_text(records.get(name,[])) or '').upper() for name in ('CorporateIdentityNumber','NSESymbol','ISIN')}
    if not re.fullmatch(r'[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}',result['CorporateIdentityNumber'] or '') or not result['NSESymbol'] or not re.fullmatch(r'IN[A-Z0-9]{10}',result['ISIN'] or ''):raise ValueError('Missing/invalid exact issuer identity')
    return {'cin':result['CorporateIdentityNumber'],'symbol':result['NSESymbol'],'isin':result['ISIN']}

def parse_annual(body,metadata,crosswalk):
    root=xml_root(body);data=facts(root)
    def texts(tag):return [e for (name,_),elements in data.items() if name==tag for e in elements]
    symbol=(unique_text(texts('Symbol')+texts('NSESymbol')) or '').upper();isin=(unique_text(texts('ISIN')) or '').upper()
    if symbol!=metadata['symbol'] or not isin:raise ValueError('Filing symbol/ISIN does not match the export')
    issuer=crosswalk.get((symbol,isin))
    if not issuer:raise ValueError('No verified CIN for the exact symbol/ISIN pair')
    cin=issuer['cin'];units={}
    for element in root:
        if element.tag==NS+'unit':
            measures=list(element.iter(NS+'measure'))
            if len(measures)==1 and measures[0].text and measures[0].text.split(':')[-1]=='INR' and not list(element.iter(NS+'divide')):units[element.get('id')]='INR'
    contexts={}
    for element in root:
        if element.tag!=NS+'context':continue
        if any(local(e.tag) in ('explicitMember','typedMember') for e in element.iter()):continue
        period=element.find(NS+'period')
        if period is None:continue
        start=period.findtext(NS+'startDate');end=period.findtext(NS+'endDate');instant=period.findtext(NS+'instant')
        contexts[element.get('id')]={'start':start,'end':end,'instant':instant}
    def number(tags,context_ids):
        values=[]
        for tag in tags:
            for context in context_ids:
                for element in data.get((tag,context),[]):
                    if element.get(NIL) in ('true','1') or not (element.text or '').strip():continue
                    if element.get('unitRef') not in units:raise ValueError('Unsupported monetary unit in '+tag)
                    try:value=Decimal(element.text.strip())
                    except InvalidOperation:raise ValueError('Invalid monetary fact') from None
                    if not value.is_finite():raise ValueError('Non-finite monetary fact')
                    values.append(value)
            if values:break
        if len(set(values))>1:raise ValueError('Conflicting monetary facts')
        return str(values[0]) if values else ''
    banking=any(local(element.tag)=='schemaRef' and 'banking' in element.get('{http://www.w3.org/1999/xlink}href','').lower() for element in root) or ('_BANKING_' in metadata['url'].upper() and bool(texts('InterestEarned')) and bool(texts('Income')))
    reports=[]
    for context,period in contexts.items():
        if not period['start'] or not period['end']:continue
        start=date.fromisoformat(period['start']);end=date.fromisoformat(period['end'])
        try:next_year=start.replace(year=start.year+1)
        except ValueError:continue
        if next_year-timedelta(days=1)!=end:continue
        basis_text=unique_text(data.get(('NatureOfReportStandaloneConsolidated',context),[]))
        basis={'Standalone':'standalone','Consolidated':'consolidated','Non-Consolidated':'standalone'}.get(basis_text)
        if not basis or basis!=metadata['basis']:raise ValueError('Annual reporting basis missing or conflicts with export')
        # Segment facts are excluded. XBRL decimals/rounding describe precision, not a currency multiplier.
        instant_ids=[key for key,value in contexts.items() if value['instant']==end.isoformat()]
        row={'cin':cin,'financial_year':str(end.year),'reporting_type':basis,'period_end':end.isoformat(),'period_months':'12','unit':'INR','source_id':'nse','source_url':metadata['url'],'as_of':metadata['published'],'revenue':number(['RevenueFromOperations','RevenueFromOperationsNet'],[context]),'net_profit':number(['ProfitLossForPeriod','ProfitLossForThePeriod','NetProfitLossForThePeriod'],[context]),'expenses':number(['Expenses','TotalExpenses'],[context]),'ebitda':number(['EarningsBeforeInterestTaxDepreciationAndAmortisation','EarningsBeforeInterestTaxDepreciationAndAmortization'],[context]),'assets':number(['Assets','TotalAssets'],instant_ids),'liabilities':number(['Liabilities','TotalLiabilities'],instant_ids)}
        row['revenue_metric']='revenue_from_operations'
        if not row['revenue'] and banking:
            row['revenue']=number(['Income','TotalIncome'],[context]);row['revenue_metric']='total_income_banking'
        if row['revenue'] or row['net_profit']:reports.append(row)
    if not reports:raise ValueError('No supported annual 12-month monetary context')
    return reports
