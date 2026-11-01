/* Annual CIN-matched statements. Preserve units, reporting basis, dates and missing values. */
'use strict';
(() => {
  const validDate=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
  const fields=['revenue_metric','financial_year','reporting_type','revenue_inr','profit_inr','assets_inr','liabilities_inr','revenue_growth','profit_growth','financial_source','financial_as_of','financial_period_end','financial_source_id'];
  const multipliers={'INR':1,'INR lakh':100000,'INR crore':10000000};
  class Statements{
    constructor(records=[]){this.byCin=new Map();const keys=new Set();for(const row of records){
      if(!/^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$/.test(row.cin)||!['standalone','consolidated'].includes(row.reporting_type)||!Object.hasOwn(multipliers,row.unit)||row.period_months!==12||!validDate(row.period_end)||row.financial_year!==Number(row.period_end.slice(0,4))||!validDate(row.as_of)||row.as_of<row.period_end||!String(row.source_url).startsWith('https://'))throw Error('Financial statement identity, period, basis or source is invalid.');
      if(!['reported_revenue','revenue_from_operations','total_income_banking'].includes(row.revenue_metric||'reported_revenue'))throw Error('Unknown financial revenue definition.');
      const source=new URL(row.source_url);if(source.protocol!=='https:'||!source.hostname||source.username||source.password||row.revenue==null&&row.net_profit==null)throw Error('Financial statement requires a source and at least one financial figure.');
      for(const field of ['revenue','net_profit','assets','liabilities','expenses','ebitda'])if(row[field]!=null&&(typeof row[field]!=='number'||!Number.isFinite(row[field]*multipliers[row.unit])))throw Error('Financial statement contains a non-finite amount.');
      const key=[row.cin,row.financial_year,row.reporting_type].join('|');if(keys.has(key))throw Error('Financial statement contains duplicate CIN/year/basis records.');keys.add(key);
      if(!this.byCin.has(row.cin))this.byCin.set(row.cin,[]);this.byCin.get(row.cin).push(row);
    }for(const rows of this.byCin.values())rows.sort((a,b)=>b.financial_year-a.financial_year);}
    history(cin){return this.byCin.get(cin)||[];}
    attach(row,params=new URLSearchParams()){
      for(const field of fields)row[field]=null;
      const basis=params.get('reporting_type')||'standalone',fy=params.get('fy'),rows=this.history(row.cin).filter(record=>record.reporting_type===basis),statement=rows.find(record=>!fy||String(record.financial_year)===fy);
      if(!statement)return row;
      const multiplier=multipliers[statement.unit];row.revenue_metric=statement.revenue_metric||'reported_revenue';row.financial_year=statement.financial_year;row.reporting_type=basis;row.financial_source=statement.source_url;row.financial_source_id=statement.source_id;row.financial_as_of=statement.as_of;row.financial_period_end=statement.period_end;
      for(const [source,target]of [['revenue','revenue_inr'],['net_profit','profit_inr'],['assets','assets_inr'],['liabilities','liabilities_inr']])row[target]=statement[source]==null?null:statement[source]*multiplier;
      const previous=rows.find(record=>record.financial_year===statement.financial_year-1&&(record.period_end.slice(5)===statement.period_end.slice(5)||(['02-28','02-29'].includes(record.period_end.slice(5))&&['02-28','02-29'].includes(statement.period_end.slice(5)))));
      if(previous){for(const [source,target]of [['revenue','revenue_growth'],['net_profit','profit_growth']]){if(source==='revenue'&&(previous.revenue_metric||'reported_revenue')!==row.revenue_metric)continue;const old=previous[source]==null?null:previous[source]*multipliers[previous.unit],now=statement[source]==null?null:statement[source]*multiplier;if(old!=null&&old>0&&now!=null){const growth=(now/old-1)*100;if(Number.isFinite(growth))row[target]=growth;}}}
      return row;
    }
  }
  const api={Statements,fields};if(typeof window!=='undefined')window.AtlasFinancial=api;else self.AtlasFinancial=api;
})();
