import pytest
from intelligence.web_revenue import extract
from tests.test_screener_financials import sample


def test_unverified_lead_retains_period_source_and_unknown_basis():
    lead=extract(sample(basis=''),cin='L99999GJ1987PLC009768',company_name='Target Ltd',source_company_name='Target Limited',symbol='TEST',source_url='https://www.screener.in/company/TEST/',observed_on='2026-11-01')
    assert lead['verification_status']=='unverified' and lead['confidence']=='low'
    assert lead['reporting_basis']=='unspecified' and lead['period_end']=='2026-03-31'
    assert lead['revenue_inr']==12345600000 and 'CIN not confirmed' in lead['match_basis']
    assert lead['source_company_name']=='Target Limited'


def test_wrong_symbol_or_unrecognized_units_cannot_become_a_lead():
    for html in [sample(symbol='WRONG'),sample(unit='Dollars')]:
        with pytest.raises(ValueError):extract(html,cin='L99999GJ1987PLC009768',company_name='Target',source_company_name='Target',symbol='TEST',source_url='https://www.screener.in/company/TEST/',observed_on='2026-11-01')


def test_share_classes_deduplicate_and_conflicting_sources_are_excluded():
    from intelligence.web_revenue import unique_leads
    one=dict(cin='A',revenue_inr=100,period_end='2026-03-31',reporting_basis='standalone',source_url='https://www.screener.in/company/A/')
    duplicate=one|{'source_url':'https://www.screener.in/company/ADVR/'}
    leads,conflicts=unique_leads([one,duplicate]);assert len(leads)==1 and not conflicts
    assert leads[0]['source_url']==one['source_url'] and leads[0]['alternate_source_urls']==[duplicate['source_url']]
    leads,conflicts=unique_leads([one,duplicate|{'revenue_inr':200}]);assert not leads and conflicts==['A']
