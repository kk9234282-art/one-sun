"""Synthetic XBRL only: annual periods, INR facts and exact issuer identity."""
import pytest
from intelligence.nse_financials import parse_annual,identity
CIN='L12345MH2010PLC000001';SYMBOL='SYNTHETIC';ISIN='INE123A01010'
META={'symbol':SYMBOL,'basis':'standalone','url':'https://nsearchives.nseindia.com/synthetic.xml','published':'2026-05-20'}
CROSS={(SYMBOL,ISIN):{'cin':CIN}}

def document(extra='',unit='iso4217:INR',end='2026-03-31',basis='Standalone'):
 return f'''<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:f="urn:synthetic" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <xbrli:context id="Annual"><xbrli:entity><xbrli:identifier scheme="urn:exchange">{SYMBOL}</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2025-04-01</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="Quarter"><xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:context id="Instant"><xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period></xbrli:context>
 <xbrli:context id="Segment"><xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="f:Segment">f:Part</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2025-04-01</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:unit id="Money"><xbrli:measure>{unit}</xbrli:measure></xbrli:unit>
 <f:Symbol contextRef="Annual">{SYMBOL}</f:Symbol><f:ISIN contextRef="Annual">{ISIN}</f:ISIN>
 <f:NatureOfReportStandaloneConsolidated contextRef="Annual">{basis}</f:NatureOfReportStandaloneConsolidated>
 <f:RevenueFromOperations contextRef="Quarter" unitRef="Money">99999999</f:RevenueFromOperations>
 <f:RevenueFromOperations contextRef="Segment" unitRef="Money">88888888</f:RevenueFromOperations>
 <f:RevenueFromOperations contextRef="Annual" unitRef="Money" decimals="-5">10000000</f:RevenueFromOperations>
 <f:ProfitLossForPeriod contextRef="Annual" unitRef="Money">-200000</f:ProfitLossForPeriod>
 <f:Assets contextRef="Instant" unitRef="Money">50000000</f:Assets>
 {extra}</xbrli:xbrl>'''.encode()

def test_annual_context_only_and_decimals_are_not_scale():
 rows=parse_annual(document(),META,CROSS);assert len(rows)==1;row=rows[0]
 assert row['cin']==CIN and row['unit']=='INR' and row['revenue']=='10000000' and row['net_profit']=='-200000'
 assert row['assets']=='50000000' and row['liabilities']=='' and row['financial_year']=='2026'

@pytest.mark.parametrize('kwargs',[{'end':'2026-02-28'},{'unit':'iso4217:USD'},{'basis':'Consolidated'}])
def test_wrong_period_currency_or_basis_rejected(kwargs):
 with pytest.raises(ValueError):parse_annual(document(**kwargs),META,CROSS)

def test_exact_bridge_required():
 with pytest.raises(ValueError,match='verified CIN'):parse_annual(document(),META,{})
 with pytest.raises(ValueError,match='symbol/ISIN'):parse_annual(document(),dict(META,symbol='OTHER'),CROSS)

def test_conflicting_facts_and_entities_rejected():
 with pytest.raises(ValueError,match='Conflicting monetary'):parse_annual(document('<f:RevenueFromOperations contextRef="Annual" unitRef="Money">11</f:RevenueFromOperations>'),META,CROSS)
 with pytest.raises(ValueError,match='entity'):parse_annual(b'<!DOCTYPE x SYSTEM "file:///etc/passwd">',META,CROSS)

def test_issuer_identity():
 body=f'<x xmlns:f="urn:synthetic"><f:CorporateIdentityNumber>{CIN}</f:CorporateIdentityNumber><f:NSESymbol>{SYMBOL}</f:NSESymbol><f:ISIN>{ISIN}</f:ISIN></x>'.encode()
 assert identity(body)=={'cin':CIN,'symbol':SYMBOL,'isin':ISIN}


def test_banking_income_retains_its_definition_and_pat_tag():
 body=document().replace(b'RevenueFromOperations',b'Income').replace(b'ProfitLossForPeriod',b'ProfitLossForThePeriod')
 body=body.replace(b'<xbrli:unit',b'<link:schemaRef xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="banking_entry_point_2020.xsd"/><xbrli:unit',1)
 row=parse_annual(body,META,CROSS)[0]
 assert row['revenue']=='10000000' and row['revenue_metric']=='total_income_banking' and row['net_profit']=='-200000'
 nonbank=document().replace(b'RevenueFromOperations',b'Income')
 assert parse_annual(nonbank,META,CROSS)[0]['revenue']==''
