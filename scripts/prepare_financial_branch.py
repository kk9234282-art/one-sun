"""Publish a validated real financial overlay; never create financial sample data."""
import argparse,gzip,hashlib,json,os,re,subprocess
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--branch',default='data/listed-financials-v1');args=parser.parse_args()
    if not re.fullmatch(r'data/listed-financials-v[1-9][0-9]*',args.branch):raise SystemExit('Use a versioned data/listed-financials-vN branch.')
    root=Path(__file__).resolve().parents[1];os.chdir(root);folder=root/'instance/build/listed-financials';manifest=json.loads((folder/'manifest.json').read_text());report=json.loads((folder/'validation-report.json').read_text());catalog_path=root/'deployment/national/catalog.json';catalog=json.loads(catalog_path.read_text())
    assert report['rejected_rows']==0 and report['input_sha256']==manifest['input_sha256'],'Validation report must match the prepared data without rejected rows'
    assert manifest['source_data_commit']==catalog['data_commit'] and manifest['schema_version']==1
    body=(folder/manifest['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==manifest['sha256'];records=json.loads(gzip.decompress(body));assert len(records)==manifest['rows']>0
    env=os.environ.copy();env['GIT_INDEX_FILE']=str(root/'instance/build/financial-branch.index')
    def git(*args,input=None):return subprocess.check_output(['git',*args],input=input,env=env).decode().strip()
    git('read-tree','--empty')
    readme='# CIN-matched annual listed-company financial statements\n\nEach row retains annual period, units, standalone/consolidated basis, source URL and publication date. Joined by CIN to company snapshot '+catalog['data_commit']+'. Source labels describe supplied references; figures are not inferred from capital or company names. No accounts or local database files included.\n'
    for path,contents in [('deployment/financials/'+manifest['path'],body),('deployment/financials/manifest.json',json.dumps(manifest,separators=(',',':')).encode()),('deployment/financials/validation-report.json',json.dumps(report,separators=(',',':')).encode()),('vercel.json',b'{"git":{"deploymentEnabled":false}}\n'),('DATASET.md',readme.encode())]:
        blob=git('hash-object','-w','--stdin',input=contents);git('update-index','--add','--cacheinfo','100644',blob,path)
    tree=git('write-tree');existing=subprocess.run(['git','rev-parse','--verify','refs/heads/'+args.branch],capture_output=True,text=True)
    if existing.returncode==0:
        commit=existing.stdout.strip();assert git('rev-parse',commit+'^{tree}')==tree,'Use a new version for changed data'
    else:
        commit=git('commit-tree',tree,'-m','Publish validated annual listed-company financial statements');git('update-ref','refs/heads/'+args.branch,commit)
    catalog['financials']={**manifest,'path':f'https://raw.githubusercontent.com/kk9234282-art/one-sun/{commit}/deployment/financials/'+manifest['path'],'data_commit':commit,'data_branch':args.branch}
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    print(json.dumps({'branch':args.branch,'commit':commit,'covered_companies':manifest['covered_companies'],'statements':len(records),'latest_publication_date':manifest['latest_publication_date']}))
if __name__=='__main__':main()
