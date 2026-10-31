/* Public read-only transport for the same dashboard UI. No server credentials. */
'use strict';
(() => {
  let activeData,localOverride=false;
  const ready = window.AtlasOnline?.enabled?Promise.resolve(activeData={manifest:{record_count:0},fields:['cin','name','class','registered_class','category','subcategory','status','incorporated','address','state','district','industry','nic','roc','postal_code','authorised_capital','paid_up_capital','effective_listing','source_id','as_of'],companies:[],byCin:new Map(),sources:[],datasets:[]}):fetch('/data/companies.json').then(async response => {
    if (!response.ok) throw new Error('Published company data could not be loaded.');
    const data = await response.json();
    if (data.manifest.publication_mode !== 'authorised-public-dataset') throw new Error('Unexpected dataset format.');
    data.companies = data.rows.map(values => {
      const row = Object.fromEntries(data.fields.map((field, i) => [field, values[i]]));
      for (const field of ['financial_year', 'reporting_type', 'revenue_inr', 'profit_inr', 'assets_inr', 'liabilities_inr', 'revenue_growth', 'profit_growth', 'financial_source', 'financial_as_of']) row[field] = null;
      return row;
    });
    if (new Set(data.companies.map(row => row.cin)).size !== data.manifest.record_count) throw new Error('Dataset identity count does not reconcile.');
    data.byCin = new Map(data.companies.map(row => [row.cin, row]));
    delete data.rows;
    activeData=data;
    return data;
  });
  const inactive = new Set(['Strike Off','Struck Off','Dormant','Dissolved','Under Liquidation','Inactive','Amalgamated','Converted To Llp','Dissolved (Liquidated)','Dormant Under Section 455','Dissolved Under Section 59(8)','Dissolved Under Section 54']);
  const weights = { revenue_growth:25, profitability:20, financial_stability:20, business_history:15, corporate_compliance:10, industry_prospects:10 };
  const notice = 'Partial research indicator, not an official SEBI IPO eligibility test or investment recommendation. Missing evidence is unscored; points are not normalized to 100.';
  const analysisDate=row=>row.incorporated&&row.incorporated!=='1111-11-11'&&row.incorporated<=(row.as_of||new Date().toISOString().slice(0,10))?row.incorporated:null;
  const reviewed=row=>analysisDate(row)||!row.incorporated?{...row}:{...row,source_incorporated:row.incorporated,incorporated:null,data_quality:'Implausible source date retained but withheld from date analyses and age scores; no corrected date inferred.'};
  const age = row => analysisDate(row) ? (Date.now() - Date.parse(analysisDate(row) + 'T00:00:00Z')) / (365.2425 * 86400000) : null;
  function score(row) {
    const years = age(row);
    const points = years === null ? null : Math.round(Math.max(0, Math.min(1, years / 10)) * 1500) / 100;
    return { observed_points:points || 0, assessable_points:points === null ? 0 : 15, maximum:100,
      factors:Object.fromEntries(Object.entries(weights).map(([key, maximum]) => [key, { maximum, points:key === 'business_history' ? points : null }])), notice };
  }
  function selected(data, params) {
    const exact = ['state','industry','class','status','district','nic'];
    const q = (params.get('q') || '').toLowerCase();
    return data.companies.filter(row => {
      if (q && !row.name.toLowerCase().includes(q) && !row.cin.toLowerCase().includes(q)) return false;
      for (const field of exact) if (params.get(field) && row[field] !== params.get(field)) return false;
      if (params.get('listing') && row.effective_listing !== params.get('listing')) return false;
      for (const field of ['incorporated','as_of']) {
        const value=field==='incorporated'?analysisDate(row):row[field];
        if (params.get(field + '_from') && (!value || value < params.get(field + '_from'))) return false;
        if (params.get(field + '_to') && (!value || value > params.get(field + '_to'))) return false;
      }
      const numeric = { min_revenue:'revenue_inr', min_profit:'profit_inr', min_revenue_growth:'revenue_growth', min_profit_growth:'profit_growth', min_capital:'paid_up_capital' };
      for (const [key, field] of Object.entries(numeric)) {
        if (params.get(key) !== null && params.get(key) !== '') {
          const threshold = Number(params.get(key));
          if (!Number.isFinite(threshold)) throw new Error('Numeric filters must be finite.');
          if (row[field] === null || row[field] < threshold) return false;
        }
      }
      if (params.get('positive_profit') === '1' && !(row.profit_inr > 0)) return false;
      if (params.get('min_age') && (age(row) === null || age(row) < Number(params.get('min_age')))) return false;
      return true;
    });
  }
  function sorted(rows, params) {
    const field = params.get('sort') || 'name';
    const allowed = ['name','cin','incorporated','paid_up_capital','revenue_inr','profit_inr','revenue_growth','as_of'];
    if (!allowed.includes(field)) throw new Error('Invalid sort column.');
    const direction = params.get('direction') === 'desc' ? -1 : 1;
    return [...rows].sort((a, b) => {
      if (a[field] == null && b[field] != null) return 1;
      if (b[field] == null && a[field] != null) return -1;
      const cmp = typeof a[field] === 'number' ? a[field] - b[field] : String(a[field] || '').localeCompare(String(b[field] || ''), 'en');
      return cmp * direction || a.cin.localeCompare(b.cin);
    });
  }
  function directory(data, params, screening=false) {
    if (screening) params.set('listing','unlisted');
    const rows = sorted(selected(data,params), params);
    const page = Math.max(1, Number(params.get('page')) || 1);
    const per_page = Math.min(100, Math.max(1, Number(params.get('per_page')) || 25));
    const visible = rows.slice((page-1)*per_page, page*per_page).map(row => screening ? {...reviewed(row), research_score:score(row)} : reviewed(row));
    return { rows:visible, total:rows.length, page, per_page, ...(screening ? {methodology:{weights, notice}} : {}) };
  }
  function grouping(rows, field) {
    const counts = new Map();
    for (const row of rows) {
      const label = typeof field === 'function' ? field(row) : row[field] || 'Unknown';
      counts.set(label, (counts.get(label) || 0) + 1);
    }
    return [...counts].map(([label,count]) => ({label,count})).sort((a,b) => b.count-a.count || a.label.localeCompare(b.label));
  }
  function overview(data, params) {
    const rows = selected(data,params), count = predicate => rows.filter(predicate).length;
    const dates = rows.map(row=>row.as_of).filter(Boolean).sort();
    const summary = { companies:rows.length, active:count(row=>row.status==='Active'), inactive:count(row=>inactive.has(row.status)),
      other_status:count(row=>row.status!=='Active'&&!inactive.has(row.status)), private:count(row=>row.class==='Private'), public:count(row=>row.class==='Public'),
      listed:count(row=>row.effective_listing==='listed'), unlisted:count(row=>row.effective_listing==='unlisted'), unknown_listing:count(row=>row.effective_listing==='unknown'),
      financial_coverage:0, oldest:dates[0]||null, newest:dates[dates.length-1]||null, llps:0, msmes:0, securities:0, unlinked_securities:0 };
    const groups = Object.fromEntries(['state','industry','class','effective_listing','status'].map(field=>[field,grouping(rows,field)]));
    groups.trends = grouping(rows.filter(row=>analysisDate(row)),row=>analysisDate(row).slice(0,4)).sort((a,b)=>a.label.localeCompare(b.label));
    groups.capital = grouping(rows,row=>row.paid_up_capital==null?'Unknown':row.paid_up_capital<1e7?'< ₹1 crore':row.paid_up_capital<1e8?'₹1–10 crore':'≥ ₹10 crore');
    return {summary,groups,datasets:data.datasets};
  }
  window.AtlasSnapshot = {
    async restorePublished(){localOverride=false;activeData=await ready;window.dispatchEvent(new Event('atlas-data-changed'));},
    async request(path, options={}) {
      if(window.AtlasIndia?.active)return window.AtlasIndia.request(path,options);
      if(window.AtlasOnline?.enabled&&!localOverride)return window.AtlasOnline.request(path,options);
      if (options.method && options.method !== 'GET') throw new Error('This public deployment is read-only. Use the full application to import or update data.');
      await ready;
      const data = activeData, url = new URL(path, location.origin), params = url.searchParams;
      switch (url.pathname) {
        case '/api/options': return Object.fromEntries(['state','industry','class','status','district','nic'].map(field=>[field,[...new Set(data.companies.map(row=>row[field]).filter(Boolean))].sort()]));
        case '/api/companies': return directory(data,params);
        case '/api/screen': return directory(data,params,true);
        case '/api/overview': return overview(data,params);
        case '/api/sources': return {sources:data.sources,imports:[]};
      }
      if (url.pathname.startsWith('/api/records/')) return {rows:[],total:0,page:Number(params.get('page'))||1,per_page:50};
      if (url.pathname.startsWith('/api/company/')) {
        const row = data.byCin.get(decodeURIComponent(url.pathname.split('/').pop()));
        if (!row) throw new Error('Company not found in published data.');
        return {company:reviewed(row),score:score(row),field_sources:[],financials:[],historical_names:[],securities:[],directors:[],filings:[],company_history:[],financial_history:[]};
      }
      throw new Error('This action is unavailable in the read-only dataset deployment.');
    }
  };
  // Download the complete filtered selection, not just the visible page.
  document.addEventListener('click',async event=>{
    const anchor = event.target.closest('a');
    if (!anchor || !anchor.getAttribute('href')?.startsWith('/api/export.')) return;
    event.preventDefault();event.stopImmediatePropagation();
    try {
      if(window.AtlasIndia?.active){await window.AtlasIndia.exportCSV(new URL(anchor.href).searchParams);return;}
      if(window.AtlasOnline?.enabled&&!localOverride){await window.AtlasOnline.exportCSV(new URL(anchor.href).searchParams);return;}
      await ready;
      const data = activeData, params = new URL(anchor.href).searchParams;
      const rows = sorted(selected(data,params),params);
      const safe = value => {
        let text = value == null ? '' : String(value);
        if (typeof value==='string' && /^[\s]*[=+\-@]/.test(text)) text="'"+text;
        return '"'+text.replaceAll('"','""')+'"';
      };
      const contents = '\ufeff'+[data.fields.map(safe).join(','),...rows.map(row=>data.fields.map(field=>safe(row[field])).join(','))].join('\r\n');
      const blob = URL.createObjectURL(new Blob([contents],{type:'text/csv;charset=utf-8'}));
      const link = document.createElement('a');link.href=blob;link.download='companies.csv';link.click();setTimeout(()=>URL.revokeObjectURL(blob),3000);
    } catch(error) { const target=document.querySelector('#error');target.textContent=error.message;target.classList.remove('hidden'); }
  },true);
  const excel=document.querySelector('#export-xlsx');if(excel)excel.hidden=true;
  const count=document.querySelector('#result-count');if(count)count.textContent='Loading published company records…';
  const localForm=document.querySelector('#local-csv-form');
  if(localForm){
    const status=document.querySelector('#local-csv-status'),parts=document.querySelector('#local-parts');
    const cancel=document.querySelector('#local-csv-cancel'),restore=document.querySelector('#local-csv-restore');
    let worker=null,lastImport=null,generation=0;
    const refresh=()=>window.dispatchEvent(new Event('atlas-data-changed'));
    document.querySelector('#local-csv-file').addEventListener('change',event=>{
      const match=event.target.files[0]?.name.match(/\d{4}-\d{2}-\d{2}/);
      if(match)document.querySelector('#local-csv-date').value=match[0];
    });
    cancel.addEventListener('click',()=>{generation++;worker?.terminate();worker=null;localForm.querySelector('button[type=submit]').disabled=false;cancel.hidden=true;status.textContent='Cancelled. Previously loaded records were retained.';});
    restore.addEventListener('click',async()=>{generation++;worker?.terminate();worker=null;localOverride=false;activeData=await ready;lastImport=null;parts.replaceChildren();status.textContent='Restored the published dataset. Local CSV changes were discarded.';cancel.hidden=true;localForm.querySelector('button[type=submit]').disabled=false;refresh();});
    localForm.addEventListener('submit',async event=>{
      event.preventDefault();
      const file=document.querySelector('#local-csv-file').files[0],asOf=document.querySelector('#local-csv-date').value;
      if(!file||!asOf)return;
      await ready;
      worker?.terminate();
      const job=++generation;
      const base=activeData,incoming=new Map(),exceptions=[];let fields=[],headers=[],duplicateRows=0;
      const submit=localForm.querySelector('button[type=submit]');submit.disabled=true;cancel.hidden=false;parts.replaceChildren();
      status.textContent='Reading the CSV locally in a background worker. No file upload is being sent.';
      worker=new Worker('/static/csv-worker.js');
      const fail=message=>{if(job!==generation)return;worker?.terminate();worker=null;submit.disabled=false;cancel.hidden=true;status.textContent='Could not load the file: '+message+'. Previous dataset retained.';};
      worker.onerror=event=>fail(event.message||'Worker failed; try a desktop browser with more available memory');
      worker.onmessage=event=>{
        if(job!==generation)return;
        const message=event.data;
        if(message.type==='headers'){fields=message.fields;headers=message.headers;}
        if(message.type==='batch'){
          const index=fields.indexOf('cin');
          for(const values of message.rows){if(incoming.has(values[index]))duplicateRows++;incoming.set(values[index],values);}
          exceptions.push(...message.exceptions);
        }
        if(message.type==='progress')status.textContent=`Reading locally: ${Math.floor(message.bytes/message.total*100)}% · ${message.accepted.toLocaleString('en-IN')} valid rows · ${message.rejected.toLocaleString('en-IN')} exceptions. Nothing uploaded.`;
        if(message.type==='error')fail(message.message);
        if(message.type==='complete'){
          const merged=new Map(base.byCin);let added=0,updated=0,stale=0;
          for(const [cin,values]of incoming){
            const row=Object.fromEntries(fields.map((field,i)=>[field,values[i]])),previous=merged.get(cin);
            if(previous?.as_of>asOf){stale++;continue;}
            const company={...(previous||{})};
            for(const [key,value]of Object.entries(row))if(value!==null)company[key]=value;
            for(const key of fields)if(!(key in company))company[key]=null;
            for(const key of ['financial_year','reporting_type','revenue_inr','profit_inr','assets_inr','liabilities_inr','revenue_growth','profit_growth','financial_source','financial_as_of'])company[key]=null;
            if(company.effective_listing==null)company.effective_listing='unknown';
            merged.set(cin,company);if(previous)updated++;else added++;
          }
          localOverride=true;
          activeData={...base,companies:[...merged.values()],byCin:merged,manifest:{...base.manifest,record_count:merged.size},datasets:[{
            title:'Local CSV: '+file.name,scope:`This browser only. ${incoming.size.toLocaleString('en-IN')} distinct valid CINs from the selected file; merged by CIN with previously loaded records. State-wide completeness has not been independently verified.`,
            date_basis:asOf+' is the user-selected snapshot label, not an independently verified publication date.',provenance:'User-selected local file; no file contents uploaded to this site.'
          },...base.datasets]};
          lastImport={incoming,fields,headers,exceptions,asOf,filename:file.name};
          status.textContent=`Loaded in this browser only: ${incoming.size.toLocaleString('en-IN')} unique valid companies · ${added.toLocaleString('en-IN')} added · ${updated.toLocaleString('en-IN')} updated · ${exceptions.length.toLocaleString('en-IN')} exceptions · ${duplicateRows.toLocaleString('en-IN')} duplicate rows (last valid row retained) · ${stale} older records retained. Reloading the page discards this local load. Use Create smaller files below to transfer the data for permanent publication.`;
          worker.terminate();worker=null;submit.disabled=false;cancel.hidden=true;refresh();
        }
      };
      worker.postMessage({file,asOf});
    });
    const save=(contents,name,type='text/csv;charset=utf-8')=>{
      const link=document.createElement('a'),url=URL.createObjectURL(new Blob([contents],{type}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);
    };
    const csvCell=value=>'"'+String(value??'').replaceAll('"','""')+'"';
    document.querySelector('#local-create-parts').addEventListener('click',async event=>{
      if(!lastImport){status.textContent='Load a local CSV first.';return;}
      event.target.disabled=true;parts.replaceChildren();
      try{
        const imported=lastImport,rows=[...imported.incoming.values()],columns=imported.fields.map(field=>field==='effective_listing'?'listing_status':field);
        const header=columns.map(csvCell).join(',')+'\n',encoder=new TextEncoder(),limit=8*1024*1024;
        const line=values=>values.map(csvCell).join(',')+'\n';
        const chunks=[];let start=0,size=encoder.encode(header).byteLength;
        for(let i=0;i<rows.length;i++){
          const bytes=encoder.encode(line(rows[i])).byteLength;
          if(size+bytes>limit&&i>start){chunks.push([start,i]);start=i;size=encoder.encode(header).byteLength;}
          if(size+bytes>limit)throw Error('A single normalized row exceeds 8 MiB. Inspect that source record.');
          size+=bytes;
          if(i%2000===0){if(lastImport!==imported)throw Error('Preparation cancelled because the local dataset changed.');status.textContent='Preparing smaller files: '+Math.round(i/Math.max(1,rows.length)*100)+'%. No file upload is being sent.';await new Promise(resolve=>setTimeout(resolve,0));}
        }
        if(start<rows.length)chunks.push([start,rows.length]);
        chunks.forEach(([from,to],i)=>{
          const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=`Download part ${i+1} of ${chunks.length} (${(to-from).toLocaleString('en-IN')} companies)`;
          button.addEventListener('click',()=>save(header+rows.slice(from,to).map(line).join(''),`companies-${imported.asOf}-part-${String(i+1).padStart(3,'0')}.csv`));parts.append(button,document.createTextNode(' '));
        });
        if(imported.exceptions.length){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='Download exceptions separately';button.addEventListener('click',()=>save(['source_record,validation_error,'+imported.headers.map(csvCell).join(','),...imported.exceptions.map(row=>[row.record,row.reason,...row.values].map(csvCell).join(','))].join('\n'),'company-csv-exceptions.csv'));parts.append(button);}
        status.textContent=`Prepared ${chunks.length} file(s), each at most 8 MiB, containing only the selected file's unique valid companies. Download each part and attach those files in this chat to update the shared dashboard. Snapshot label: ${imported.asOf}. Exceptions stay separate. These transfer files contain original field text; do not execute spreadsheet formulas from untrusted files.`;
      }catch(error){status.textContent=error.message;}finally{event.target.disabled=false;}
    });
  }
})();
