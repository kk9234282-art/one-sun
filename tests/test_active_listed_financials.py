from scripts.export_active_listed_financials import export,csv_bytes


def test_active_listed_financials_exact_scope_and_latest_basis():
    companies=[dict(cin=cin,name=cin,status=status,effective_listing=listing,state='Maharashtra',paid_up_capital=0) for cin,status,listing in [('A','Active','listed'),('B','Strike Off','listed'),('C','Active','unlisted'),('D','Active','listed')]]
    def row(cin,year=2026,basis='standalone'):
        return dict(cin=cin,financial_year=year,reporting_type=basis,unit='INR',period_months=12,period_end=f'{year}-03-31',as_of=f'{year}-05-01',revenue=0,net_profit=-25,source_url='https://www.nseindia.com/test')
    rows,missing,report=export({'data_commit':'fixture'},companies,[row('A',2025),row('A'),row('A',basis='consolidated'),row('B'),row('C')])
    assert len(rows)==2 and {r['reporting_type'] for r in rows}=={'standalone','consolidated'}
    assert all(r['cin']=='A' and r['financial_year']==2026 and r['revenue_or_income_inr']==0 and r['net_profit_inr']==-25 for r in rows)
    assert [r['cin'] for r in missing]==['D']
    assert report['active_listed_companies']==2 and report['covered_companies']==1 and report['remaining_companies']==1
    assert 'revenue_or_income_inr' in csv_bytes(rows).decode('utf-8-sig')
