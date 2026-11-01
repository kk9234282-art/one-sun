"""Cache the four paid-up capital views from the existing immutable index."""
import gzip,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_online_india import Stats
path=Path('deployment/national/catalog.json');catalog=json.loads(path.read_text());groups={key:Stats() for key in ['under_1cr','1_to_10cr','10cr_plus','unknown']}
for chunk in catalog['global_chunks']:
    rows=json.loads(gzip.decompress(Path('deployment/national',chunk['path']).read_bytes()))
    for values in rows:
        row={field:catalog['dictionaries'][field][value] if field in catalog['dictionaries'] else value for field,value in zip(catalog['index_fields'],values)}
        row['as_of']=catalog['as_of']
        if row['cin'] in catalog.get('date_quality',{}):row['incorporated']=None
        value=row['paid_up_capital'];band='unknown' if value is None else 'under_1cr' if value<10000000 else '1_to_10cr' if value<100000000 else '10cr_plus'
        groups[band].add(row)
result={key:stats.output() for key,stats in groups.items()}
assert sum(stats['summary']['companies'] for stats in result.values())==catalog['record_count']
expected={row['label']:row['count'] for row in catalog['stats']['groups']['capital']}
for key,label in [('under_1cr','< ₹1 crore'),('1_to_10cr','₹1–10 crore'),('10cr_plus','≥ ₹10 crore'),('unknown','Unknown')]:assert result[key]['summary']['companies']==expected.get(label,0)
catalog.setdefault('facets',{})['capital_band']=result
path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
print('Capital ranges cached:',{key:stats['summary']['companies'] for key,stats in result.items()})
