/* Public read-only transport for the same dashboard UI. No server credentials. */
'use strict';
(() => {
  const ready = fetch('/data/companies.json').then(async response => {
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
    return data;
  });
  const inactive = new Set(['Strike Off','Struck Off','Dormant','Dissolved','Under Liquidation','Inactive','Amalgamated','Converted To Llp','Dissolved (Liquidated)','Dormant Under Section 455','Dissolved Under Section 59(8)','Dissolved Under Section 54']);
  const weights = { revenue_growth:25, profitability:20, financial_stability:20, business_history:15, corporate_compliance:10, industry_prospects:10 };
  const notice = 'Partial research indicator, not an official SEBI IPO eligibility test or investment recommendation. Missing evidence is unscored; points are not normalized to 100.';
  const age = row => row.incorporated ? (Date.now() - Date.parse(row.incorporated + 'T00:00:00Z')) / (365.2425 * 86400000) : null;
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
        if (params.get(field + '_from') && (!row[field] || row[field] < params.get(field + '_from'))) return false;
        if (params.get(field + '_to') && (!row[field] || row[field] > params.get(field + '_to'))) return false;
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
    const visible = rows.slice((page-1)*per_page, page*per_page).map(row => screening ? {...row, research_score:score(row)} : {...row});
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
    groups.trends = grouping(rows.filter(row=>row.incorporated),row=>row.incorporated.slice(0,4)).sort((a,b)=>a.label.localeCompare(b.label));
    groups.capital = grouping(rows,row=>row.paid_up_capital==null?'Unknown':row.paid_up_capital<1e7?'< ₹1 crore':row.paid_up_capital<1e8?'₹1–10 crore':'≥ ₹10 crore');
    return {summary,groups,datasets:data.datasets};
  }
  window.AtlasSnapshot = {
    async request(path, options={}) {
      if (options.method && options.method !== 'GET') throw new Error('This public deployment is read-only. Use the full application to import or update data.');
      const data = await ready, url = new URL(path, location.origin), params = url.searchParams;
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
        return {company:{...row},score:score(row),field_sources:[],financials:[],historical_names:[],securities:[],directors:[],filings:[],company_history:[],financial_history:[]};
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
      const data = await ready, params = new URL(anchor.href).searchParams;
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
})();
