"""Synthetic annual tables only; never imported into the dashboard."""
import pytest
from intelligence.screener_financials import parse_annual

def sample(unit='Rs. Crores',basis='Standalone',symbol='TEST'):
    return f'''<a href="https://www.nseindia.com/get-quotes/equity?symbol={symbol}">NSE</a>
<section id="profit-loss"><p>{basis} Figures in {unit} / View Consolidated</p><table>
<tr><th></th><th data-date-key="2024-03-31">Mar 2024</th><th data-date-key="2025-03-31">Mar 2025</th><th data-date-key="2026-03-31">Mar 2026</th><th data-date-key="TTM">TTM</th></tr>
<tr><td>Sales <span>+</span></td><td>1</td><td>0</td><td>1,234.56</td><td>9,999</td></tr>
<tr><td>Net Profit</td><td>1</td><td>-5</td><td>—</td><td>9,999</td></tr></table></section>'''

def parse(html,**changes):
    return parse_annual(html,**(dict(cin='L99999GJ1987PLC009768',symbol='TEST',year=2026,published='2026-07-09',source_url='https://www.screener.in/company/TEST/',identity_url='https://nsearchives.nseindia.com/annual_reports/test.pdf',retrieved='2026-11-01')|changes))

def test_annual_unit_basis_year_and_missing():
    rows=parse(sample());assert len(rows)==2
    latest=rows[-1];assert latest['financial_year']==2026 and latest['revenue']=='12345600000.00' and latest['net_profit'] is None
    assert rows[0]['revenue']=='0' and rows[0]['net_profit']=='-50000000'
    assert latest['as_of']=='2026-07-09' and latest['source_retrieved_on']=='2026-11-01'
    assert latest['reporting_type']=='standalone' and latest['identity_source_url'].endswith('test.pdf')

def test_reject_symbol_units_basis_and_missing_annual_period():
    for html in [sample(symbol='OTHER'),sample(unit='Dollars'),sample(basis='Consolidated'),sample().replace('2025-03-31','TTM')]:
        with pytest.raises(ValueError):parse(html)
    with pytest.raises(ValueError):parse(sample(),year=2023)

def test_normalization_preserves_identity_and_retrieval_evidence():
    from intelligence.financial_data import normalize
    rows=parse(sample());normalized=normalize(rows[-1],{rows[-1]['cin']})
    assert normalized['source_id']=='screener' and normalized['identity_source_url']==rows[-1]['identity_source_url']
    for change in [dict(source_url='https://wrong.invalid/company/TEST/'),dict(identity_source_url='https://wrong.invalid/test.pdf'),dict(source_retrieved_on='2026-01-01'),dict(source_date_basis='')]:
        with pytest.raises(ValueError):normalize(rows[-1]|change,{rows[-1]['cin']})
