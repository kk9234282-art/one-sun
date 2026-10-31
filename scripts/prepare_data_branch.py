"""Prepare an immutable data-only Git branch without changing the current checkout."""
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
os.chdir(root)
catalog_path=root/'deployment/national/catalog.json';catalog=json.loads(catalog_path.read_text())
branch='data/india-index-v1'
index=root/'instance/build/data-branch.index';index.parent.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env['GIT_INDEX_FILE']=str(index)
def git(*args,input=None):return subprocess.check_output(['git',*args],input=input,env=env).decode().strip()
git('read-tree','--empty')
git('add','-f','--','deployment/national/index','deployment/national/profiles','deployment/national/exceptions.csv','deployment/national/source-report.json')
readme=f'''# All-India company-master index snapshot

Data-only branch; the website code is on main. Source: {catalog['source']['source_url']}

{catalog['record_count']:,} unique structurally valid company CINs; {catalog['source']['rejected_rows']} exception rows retained separately. Counts describe the supplied release, not a certified national census. Original states are retained in profile data; current state aliases are documented in source-report.json. No company financial statements were supplied.

Archive SHA-256: {catalog['source']['source_sha256']}

Compressed index/profile files are immutable and individually checksummed by the catalog on main. User accounts, passwords, database files, local ZIP uploads, session keys and backups are not included. The data was explicitly authorised for public sharing by the repository owner. Provider usage limits still apply.
'''
for path,contents in [('DATASET.md',readme),('vercel.json',json.dumps({'git':{'deploymentEnabled':False}},indent=2)+'\n')]:
    blob=git('hash-object','-w','--stdin',input=contents.encode())
    git('update-index','--add','--cacheinfo','100644',blob,path)
tree=git('write-tree')
existing=subprocess.run(['git','show-ref','--verify','--hash','refs/heads/'+branch],capture_output=True,text=True)
if existing.returncode==0:
    commit=existing.stdout.strip()
    if git('rev-parse',commit+'^{tree}')!=tree:raise SystemExit('Existing data branch differs. Use a new versioned branch; do not overwrite it.')
else:
    commit=git('commit-tree',tree,'-m','Publish release-derived all-India company index v1')
    git('update-ref','refs/heads/'+branch,commit)
catalog['base_url']=f'https://raw.githubusercontent.com/kk9234282-art/one-sun/{commit}/deployment/national/'
catalog['data_commit']=commit
catalog['data_branch']=branch
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps({'branch':branch,'commit':commit,'records':catalog['record_count'],'base_url':catalog['base_url']}))
