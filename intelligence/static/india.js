/* All-India ZIP controller. Records stay in this origin's IndexedDB, not GitHub. */
'use strict';
(() => {
  const form=document.querySelector('#india-zip-form');if(!form)return;
  const status=document.querySelector('#india-zip-status'),submit=form.querySelector('button[type=submit]'),cancel=document.querySelector('#india-zip-cancel');
  let activeWorker=null,stagingWorker=null,stagingName=null,generation=0,sequence=0;
  const pending=new Map(),pointer='atlas-local-india-dataset';
  function connect(){
    const worker=new Worker('/static/india-worker.js');
    worker.onmessage=event=>{
      const message=event.data;
      if(message.type==='import-progress'){if(worker===stagingWorker)status.textContent=message.phase||`Reading ZIP locally: ${Math.floor(message.compressed/message.total*100)}% · ${message.files}/${message.fileCount} CSVs verified · ${message.accepted.toLocaleString('en-IN')} valid rows · ${message.rejected.toLocaleString('en-IN')} exceptions. Writing to browser storage; nothing uploaded.`;return;}
      const waiter=pending.get(message.id);if(!waiter||waiter.worker!==worker)return;pending.delete(message.id);
      if(message.type==='failure')waiter.reject(Error(message.message));else waiter.resolve(message.value);
    };
    worker.onerror=event=>{for(const [id,waiter]of pending)if(waiter.worker===worker){pending.delete(id);waiter.reject(Error(event.message||'Local worker stopped. The previous completed dataset is retained.'));}};
    return worker;
  }
  function call(worker,action,args={}){return new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{worker,resolve,reject});worker.postMessage({id,action,...args});});}
  function stop(worker){if(!worker)return;worker.terminate();for(const [id,waiter]of pending)if(waiter.worker===worker){pending.delete(id);waiter.reject(Error('Local operation cancelled.'));}}
  function deleteDatabase(name){if(name?.startsWith('atlas-india-'))indexedDB.deleteDatabase(name);}
  function show(metadata){window.AtlasIndia.active=true;document.querySelector('#local-csv-tools').hidden=true;document.querySelector('#india-zip-report').hidden=false;document.querySelector('#india-zip-exceptions').hidden=false;status.textContent=`Local ZIP ready: ${metadata.recordCount.toLocaleString('en-IN')} unique companies · ${metadata.stats.groups.state.filter(row=>row.label!=='Unknown').length} state/UT labels · ${metadata.files.filter(file=>!file.skipped).length} company CSVs · ${metadata.duplicates.toLocaleString('en-IN')} duplicate rows reconciled · ${metadata.rejected.toLocaleString('en-IN')} exceptions. Saved in this browser only. Reopen the saved dataset after refresh; no publication or upload occurred.`;if(metadata.normalizer_version!==3)status.textContent+=' This saved dataset used older validation rules; re-import the ZIP to refresh CIN and date-quality checks.';window.dispatchEvent(new Event('atlas-data-changed'));}
  function download(contents,name,type='application/json'){const url=URL.createObjectURL(new Blob([contents],{type})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
  window.AtlasIndia={active:false,
    async request(path,options={}){if(options.method&&options.method!=='GET')throw Error('The local ZIP dataset is read-only after import.');if(!activeWorker)throw Error('Reopen or import a local ZIP dataset first.');return call(activeWorker,'request',{path});},
    async exportCSV(params){const csv=await this.request('/api/export.csv?'+params);download(csv,'local-india-companies.csv','text/csv;charset=utf-8');}
  };
  document.querySelector('#india-zip-file').addEventListener('change',event=>{const match=event.target.files[0]?.name.match(/\d{4}-\d{2}-\d{2}/);if(match)document.querySelector('#india-zip-date').value=match[0];});
  cancel.addEventListener('click',()=>{generation++;stop(stagingWorker);stagingWorker=null;deleteDatabase(stagingName);stagingName=null;submit.disabled=false;cancel.hidden=true;status.textContent='ZIP import cancelled. Previously completed data is retained.';});
  form.addEventListener('submit',async event=>{
    event.preventDefault();const file=document.querySelector('#india-zip-file').files[0],asOf=document.querySelector('#india-zip-date').value;if(!file||!asOf)return;
    const job=++generation;stop(stagingWorker);deleteDatabase(stagingName);stagingName='atlas-india-'+crypto.randomUUID();const name=stagingName;stagingWorker=connect();const worker=stagingWorker;submit.disabled=true;cancel.hidden=false;status.textContent='Inspecting ZIP directory and browser disk availability. User files are not uploaded.';
    try{
      const metadata=await call(worker,'import',{file,asOf,name});if(job!==generation)return;
      const previous=localStorage.getItem(pointer);localStorage.setItem(pointer,name);stop(activeWorker);activeWorker=worker;stagingWorker=null;stagingName=null;if(previous&&previous!==name)deleteDatabase(previous);show(metadata);
    }catch(error){if(job!==generation)return;stop(worker);stagingWorker=null;stagingName=null;deleteDatabase(name);status.textContent='ZIP import failed: '+error.message+' Previous completed data is retained.';}
    finally{if(job===generation){submit.disabled=false;cancel.hidden=true;}}
  });
  document.querySelector('#india-zip-reopen').addEventListener('click',async()=>{
    const name=localStorage.getItem(pointer);if(!name){status.textContent='No completed ZIP dataset is saved for this browser and website yet.';return;}
    const worker=connect();try{status.textContent='Opening the saved local database…';const metadata=await call(worker,'open',{name});stop(activeWorker);activeWorker=worker;show(metadata);}catch(error){stop(worker);status.textContent=error.message;}
  });
  document.querySelector('#india-zip-published').addEventListener('click',async()=>{window.AtlasIndia.active=false;stop(activeWorker);activeWorker=null;document.querySelector('#local-csv-tools').hidden=false;await window.AtlasSnapshot.restorePublished();status.textContent='Showing the published dataset. Your completed ZIP database is still saved locally; use Reopen saved ZIP dataset to switch back.';});
  document.querySelector('#india-zip-report').addEventListener('click',async()=>{try{if(!activeWorker)throw Error('Reopen a local ZIP dataset first.');download(JSON.stringify(await call(activeWorker,'report'),null,2),'local-india-zip-report.json');}catch(error){status.textContent=error.message;}});
  document.querySelector('#india-zip-exceptions').addEventListener('click',async()=>{try{if(!activeWorker)throw Error('Reopen a local ZIP dataset first.');download(JSON.stringify(await call(activeWorker,'exceptions'),null,2),'local-india-exceptions.json');}catch(error){status.textContent=error.message;}});
  if(localStorage.getItem(pointer))status.textContent='A completed local ZIP dataset is saved in this browser. Click Reopen saved ZIP dataset to use it.';
})();
