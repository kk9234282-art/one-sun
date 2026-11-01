"""Publish latest annual statements and a missing-coverage queue for Active listed CINs."""
import csv,gzip,hashlib,io,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def export(catalog,companies,statements):
    active={row['cin']:row for row in companies if row['status']=='Active' and row['effective_listing']=='listed'}
    latest={}
    for row in statements:
        if row['cin'] not in active:continue
        if row['unit']!='INR' or row['period_months']!=12:raise ValueError('Expected normalized annual INR statements')
        key=(row['cin'],row['reporting_type']);previous=latest.get(key)
        if previous is None or (row['period_end'],row['as_of'])>(previous['period_end'],previous['as_of']):latest[key]=row
    covered={key[0] for key in latest};output=[]
    for (cin,basis),row in sorted(latest.items(),key=lambda pair:(active[pair[0][0]]['name'],pair[0][1])):
        company=active[cin]
        output.append({'cin':cin,'company_name':company['name'],'master_status':'Active','listing_status':'listed','state':company['state'],'paid_up_capital_inr':company['paid_up_capital'],'financial_year':row['financial_year'],'reporting_type':basis,'period_end':row['period_end'],'currency':'INR','revenue_or_income_inr':row.get('revenue'),'revenue_metric':row.get('revenue_metric','revenue_from_operations'),'net_profit_inr':row.get('net_profit'),'assets_inr':row.get('assets'),'liabilities_inr':row.get('liabilities'),'source_url':row['source_url'],'source_publication_date':row['as_of']})
    missing=[{'cin':cin,'company_name':row['name'],'master_status':'Active','listing_status':'listed','coverage_note':'No exact-CIN annual statement imported; availability at other sources is not established.'} for cin,row in sorted(active.items(),key=lambda pair:pair[1]['name']) if cin not in covered]
    report={'source_data_commit':catalog['data_commit'],'scope':{'master_status':'Active','effective_listing':'listed'},'active_listed_companies':len(active),'covered_companies':len(covered),'remaining_companies':len(missing),'latest_statement_rows':len(output),'standalone_companies':sum(row['reporting_type']=='standalone' for row in output),'consolidated_companies':sum(row['reporting_type']=='consolidated' for row in output),'revenue_or_income_companies':len({row['cin'] for row in output if row['revenue_or_income_inr'] is not None}),'note':'Source master status is not evidence of current exchange trading status. Each reporting basis is explicit; financial years may differ. Missing values are blank, never zero-filled.'}
    return output,missing,report

def csv_bytes(rows):
    if not rows:raise ValueError('No rows to export')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')

def main():
    folder=ROOT/'deployment/national';catalog=json.loads((folder/'catalog.json').read_text())
    def read(kind,local):
        descriptor=catalog[kind];body=(ROOT/local/descriptor['path'].rsplit('/',1)[-1]).read_bytes()
        if hashlib.sha256(body).hexdigest()!=descriptor['sha256']:raise ValueError('Source checksum mismatch: '+kind)
        return json.loads(gzip.decompress(body))
    companies=[dict(zip(catalog['full_fields'],row)) for row in read('listed_index','instance/build/listed-index')]
    rows,missing,report=export(catalog,companies,read('financials','instance/build/listed-financials'))
    (folder/'active-listed-financials.csv').write_bytes(csv_bytes(rows));(folder/'remaining-active-listed-financials.csv').write_bytes(csv_bytes(missing))
    (folder/'active-listed-financial-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    catalog['active_listed_financials']={**report,'csv_path':'/national/active-listed-financials.csv','remaining_csv_path':'/national/remaining-active-listed-financials.csv'}
    (folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
