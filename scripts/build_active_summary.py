"""Precompute exact Active-only totals/options from the immutable national indices."""
import gzip,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_online_india import Stats
from intelligence.locality import derive,area
root=Path(__file__).resolve().parents[1];path=root/'deployment/national/catalog.json';catalog=json.loads(path.read_text());geo=json.loads((root/'deployment/cities/manifest.json').read_text())
class GeoStats(Stats):
    def __init__(self):super().__init__();self.groups.update(district=Counter(),postal_city=Counter())
    def add(self,row):super().add(row);self.groups['district'][row['district'] or 'Not identified']+=1;self.groups['postal_city'][row['postal_city'] or 'Not identified']+=1
national=Stats();states=defaultdict(GeoStats);industries=defaultdict(Stats);facets={key:defaultdict(Stats) for key in ['class','listing','capital_band']};pins=defaultdict(set);areas=defaultdict(lambda:defaultdict(Counter));locations={};fields=catalog['index_fields'];status_index=fields.index('status');active_id=catalog['dictionaries']['status'].index('Active')
for number,descriptor in enumerate(catalog['global_chunks'],1):
    rows=json.loads(gzip.decompress((root/'deployment/national'/descriptor['path']).read_bytes()));mapping=geo['global_chunks'][descriptor['path']];postal=json.loads(gzip.decompress((root/'deployment/cities'/mapping['path']).read_bytes()));assert len(rows)==len(postal)==descriptor['rows']
    assert hashlib.sha256('\n'.join(row[0] for row in rows).encode()).hexdigest()==mapping['cin_order_sha256']
    for values,pin in zip(rows,postal):
        if values[status_index]!=active_id:continue
        row={field:catalog['dictionaries'][field][value] if field in catalog['dictionaries'] else value for field,value in zip(fields,values)};row['as_of']=catalog['as_of']
        if row['cin'] in catalog.get('date_quality',{}):row['incorporated']=None
        key=(row['state'],pin)
        if key not in locations:locations[key]=(derive(pin,row['state']),area(pin,row['state']))
        row['district'],row['postal_city']=locations[key];national.add(row);states[row['state']].add(row);industries[row['industry'] or 'Unknown'].add(row)
        for field in ['class','listing']:facets[field][row['effective_listing'] if field=='listing' else row['class'] or 'Unknown'].add(row)
        capital=row['paid_up_capital'];band='unknown' if capital is None else 'under_1cr' if capital<10000000 else '1_to_10cr' if capital<100000000 else '10cr_plus';facets['capital_band'][band].add(row)
        if pin:pins[row['state']].add(pin)
        areas[row['state']][row['district'] or 'Not identified'][row['postal_city'] or 'Not identified']+=1
    if number%50==0:print('Active-only summaries:',number,'/',len(catalog['global_chunks']),flush=True)
summary={'schema_version':1,'source_data_commit':catalog['data_commit'],'status':'Active','national':national.output(),'states':{state:{'stats':stats.output(),'postal_codes':sorted(pins[state]),'areas_by_district':{district:[{'label':label,'count':count} for label,count in sorted(counts.items(),key=lambda pair:(-pair[1],pair[0]))] for district,counts in areas[state].items()}} for state,stats in states.items()},'industries':{key:stats.output() for key,stats in industries.items()},'facets':{field:{key:stats.output() for key,stats in groups.items()} for field,groups in facets.items()}}
assert summary['national']['summary']['companies']==catalog['stats']['summary']['active'];assert sum(value['stats']['summary']['companies'] for value in summary['states'].values())==summary['national']['summary']['companies']
for groups in summary['facets'].values():assert sum(value['summary']['companies'] for value in groups.values())==summary['national']['summary']['companies']
body=gzip.compress(json.dumps([summary],separators=(',',':')).encode(),compresslevel=9,mtime=0);sha=hashlib.sha256(body).hexdigest();name='active-summary-'+sha[:12]+'.json.gz';(root/'deployment/national'/name).write_bytes(body)
catalog['active_summary']={'schema_version':1,'path':'/national/'+name,'rows':1,'sha256':sha,'bytes':len(body),'source_data_commit':catalog['data_commit'],'companies':summary['national']['summary']['companies']};path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
print('Active-only companies',summary['national']['summary']['companies'],'listed',summary['facets']['listing'].get('listed',{}).get('summary',{}).get('companies'),'summary bytes',len(body),flush=True)
