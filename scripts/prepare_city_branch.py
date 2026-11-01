"""Publish only referenced, immutable locality sidecars using a separate Git index."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
folder=root/'deployment/cities';manifest=json.loads((folder/'manifest.json').read_text());catalog_path=root/'deployment/national/catalog.json';catalog=json.loads(catalog_path.read_text())
assert manifest['source_data_commit']==catalog['data_commit']
paths=['deployment/cities/manifest.json']
for state,descriptor in manifest['states'].items():
    path=folder/descriptor['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==descriptor['sha256'];paths.append(str(path.relative_to(root)))
    for chunk in json.loads(path.read_text())['chunks'].values():
        path=folder/chunk['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==chunk['sha256'];paths.append(str(path.relative_to(root)))
env=os.environ.copy();env['GIT_INDEX_FILE']=str(root/'instance/build/city-branch.index')
def git(*args,input=None):return subprocess.check_output(['git',*args],input=input,env=env).decode().strip()
git('read-tree','--empty');git('add','-f','--',*paths)
for path,body in [('vercel.json',json.dumps({'git':{'deploymentEnabled':False}})),('DATASET.md','# Address-derived locality labels\n\n'+manifest['policy']+'\n\nSource company snapshot: '+catalog['data_commit']+'\n\nSidecars align by CIN checksum with the immutable state indices. No geocoding or external city claims. Website code lives on main.\n')]:
    blob=git('hash-object','-w','--stdin',input=body.encode());git('update-index','--add','--cacheinfo','100644',blob,path)
tree=git('write-tree');branch='data/india-localities-v1'
existing=subprocess.run(['git','rev-parse','--verify','refs/heads/'+branch],capture_output=True,text=True)
if existing.returncode==0:
    commit=existing.stdout.strip();assert git('rev-parse',commit+'^{tree}')==tree,'Use a new version for changed data'
else:
    commit=git('commit-tree',tree,'-m','Publish address-derived locality sidecars v1');git('update-ref','refs/heads/'+branch,commit)
catalog['locations']={**manifest,'base_url':f'https://raw.githubusercontent.com/kk9234282-art/one-sun/{commit}/deployment/cities/','data_commit':commit,'data_branch':branch}
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'commit':commit,'matched':manifest['matched'],'unknown':manifest['unknown'],'files':len(paths)}))
