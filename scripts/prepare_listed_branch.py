"""Pin the compact listed-company index on its own immutable data branch."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root);folder=root/'instance/build/listed-index';manifest=json.loads((folder/'manifest.json').read_text());catalog_path=root/'deployment/national/catalog.json';catalog=json.loads(catalog_path.read_text());assert manifest['source_data_commit']==catalog['data_commit'];assert manifest['full_fields']==catalog['full_fields'];body=(folder/manifest['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==manifest['sha256'];assert manifest['rows']==catalog['stats']['summary']['listed']
env=os.environ.copy();env['GIT_INDEX_FILE']=str(root/'instance/build/listed-branch.index')
def git(*args,input=None):return subprocess.check_output(['git',*args],input=input,env=env).decode().strip()
git('read-tree','--empty')
files=[('deployment/listed/'+manifest['path'],body),('deployment/listed/manifest.json',json.dumps(manifest,separators=(',',':')).encode()),('vercel.json',b'{"git":{"deploymentEnabled":false}}\n'),('DATASET.md',('# Listed-company query index\n\nAn exact subset of the already public company snapshot '+catalog['data_commit']+'. Contains '+str(manifest['rows'])+' records explicitly marked listed by the supplied company master. No exchange verification or listing inference is added. PIN and source fields are retained so combined filters and exports work without scanning the national dataset. Source company fields are unchanged; existing date-quality flags still apply in the application. Website code lives on main.\n').encode())]
for path,contents in files:
    blob=git('hash-object','-w','--stdin',input=contents);git('update-index','--add','--cacheinfo','100644',blob,path)
tree=git('write-tree');branch='data/india-listed-v1';existing=subprocess.run(['git','rev-parse','--verify','refs/heads/'+branch],capture_output=True,text=True)
if existing.returncode==0:
    commit=existing.stdout.strip();assert git('rev-parse',commit+'^{tree}')==tree,'Use a new version for changed data'
else:
    commit=git('commit-tree',tree,'-m','Publish compact listed-company query index');git('update-ref','refs/heads/'+branch,commit)
catalog['listed_index']={**manifest,'path':f'https://raw.githubusercontent.com/kk9234282-art/one-sun/{commit}/deployment/listed/'+manifest['path'],'data_commit':commit,'data_branch':branch}
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'branch':branch,'commit':commit,'rows':manifest['rows'],'bytes':manifest['bytes'],'listed_below_1cr':manifest['listed_below_1cr']}))
