"""Synthetic annual statements only; never imported into published data."""
import csv
from datetime import date
import pytest
from intelligence.financial_data import normalize,build

CIN='L12345MH2010PLC000001';TODAY=date(2026,11,1)
def statement(**changes):
    return dict(cin=CIN,financial_year='2025',reporting_type='standalone',unit='INR crore',period_end='2025-03-31',period_months='12',revenue='10',net_profit='-2',assets='',liabilities='',expenses='',ebitda='',source_id='bse',source_url='https://www.bseindia.com/statement.pdf',as_of='2025-05-20')|changes

def test_loss_zero_and_source_retained():
    row=normalize(statement(revenue='0'),{CIN},TODAY)
    assert row['revenue']==0 and row['net_profit']==-2 and row['assets'] is None
    assert row['unit']=='INR crore' and row['source_url'].endswith('statement.pdf')
    assert normalize(statement(revenue=0),{CIN},TODAY)['revenue']==0

@pytest.mark.parametrize('changes',[
    {'cin':'L12345MH2010PLC000002'}, {'period_months':'3'}, {'period_end':'2025-02-30'},
    {'financial_year':'2024'}, {'reporting_type':'combined'}, {'unit':'USD'},
    {'as_of':'2025-01-01'}, {'as_of':'2026-12-01'}, {'revenue':'NaN'},
    {'net_profit':'Infinity'}, {'assets':'-1'}, {'revenue':'','net_profit':''},
    {'source_url':'http://www.bseindia.com/report'}, {'source_url':'https://example.com/report'},
    {'source_url':'https://user:password@www.bseindia.com/report'},
])
def test_bad_or_unmatched_statements_rejected(changes):
    with pytest.raises(ValueError):normalize(statement(**changes),{CIN},TODAY)

def write(path,rows):
    with path.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def test_revisions_and_reject_report(tmp_path):
    path=tmp_path/'financials.csv';write(path,[statement(),statement(as_of='2025-06-20',net_profit='-1'),statement(cin='L12345MH2010PLC000002')])
    rows,report=build(path,{CIN},TODAY)
    assert len(rows)==1 and rows[0]['net_profit']==-1
    assert report['accepted_rows']==2 and report['rejected_rows']==1 and report['covered_companies']==1
    assert report['exceptions'][0]['line']==4

def test_conflicting_same_date_fails(tmp_path):
    path=tmp_path/'conflict.csv';write(path,[statement(),statement(net_profit='20')])
    with pytest.raises(ValueError,match='Conflicting statements'):build(path,{CIN},TODAY)
