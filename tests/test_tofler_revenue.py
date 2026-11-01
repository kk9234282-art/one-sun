import pytest
from intelligence.tofler_revenue import extract
CIN='U61200MH2014FTC258522'
def parse(claim,cin=CIN):
    html=f'<p>Corporate Identification Number (CIN) of Sample is {cin}.</p><p>Sample operating revenue range is {claim} for the financial year ending on 31 March, 2024.</p><script>revenue 999999</script>'
    return extract(html,cin=CIN,company_name='Sample',source_url=f'https://www.tofler.in/sample/company/{CIN}',observed_on='2026-11-01')
def test_ranges_remain_ranges_without_invented_midpoints():
    r=parse('INR 1 cr - 100 cr');assert r['revenue_inr'] is None and r['revenue_min_inr']==10000000 and r['revenue_max_inr']==1000000000 and r['period_end']=='2024-03-31'
    r=parse('Under INR 1 cr');assert r['revenue_min_inr'] is None and r['revenue_max_inr']==10000000
    r=parse('Over INR 500 cr');assert r['revenue_min_inr']==5000000000 and r['revenue_max_inr'] is None
    assert r['verification_status']=='unverified'
def test_wrong_cin_and_paywalled_or_reversed_figures_are_rejected():
    for claim,cin in [('Details available with Pro',CIN),('USD 1 cr - 100 cr',CIN),('INR 100 cr - 1 cr',CIN),('INR 1 cr - 100 cr','U61200MH2014FTC258523')]:
        with pytest.raises(ValueError):parse(claim,cin)
