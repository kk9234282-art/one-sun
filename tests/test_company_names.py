from intelligence.company_names import candidate_key,discover_variants

def test_names_only_discover_unique_active_listed_candidates():
    assert candidate_key('A K Capital (India) Ltd.')==candidate_key('AK Capital India Limited')
    companies=[dict(cin='A',name='A K Capital (India) Ltd.',status='Active',effective_listing='listed'),dict(cin='B',name='Inactive Ltd',status='Strike Off',effective_listing='listed'),dict(cin='C',name='Unlisted Ltd',status='Active',effective_listing='unlisted')]
    exchange=[{'SYMBOL':'AK','NAME OF COMPANY':'AK Capital India Limited'},{'SYMBOL':'INACTIVE','NAME OF COMPANY':'Inactive Limited'},{'SYMBOL':'UNLISTED','NAME OF COMPANY':'Unlisted Limited'}]
    assert [r['cin'] for r in discover_variants(companies,exchange,set())]==['A']
    assert not discover_variants(companies,exchange,{'A'})
    assert not discover_variants(companies+[companies[0]|{'cin':'D'}],exchange,set())
    assert candidate_key('ABC 1 Limited')!=candidate_key('ABC 2 Limited')
