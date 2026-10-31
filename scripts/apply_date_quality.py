"""Withhold implausible source dates from analytics without inventing corrections."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import sqlite3

path=Path('deployment/national/catalog.json');catalog=json.loads(path.read_text())
if catalog.get('date_quality_applied'):
    print('Date-quality policy already applied; no duplicate adjustments.')
    raise SystemExit(0)
warnings={}
with sqlite3.connect('instance/india-online.sqlite') as db:
    for (payload,) in db.execute("SELECT payload FROM records WHERE json_extract(payload,'$.incorporated')='1111-11-11' OR json_extract(payload,'$.incorporated')>'2026-10-31'"):
        row=json.loads(payload);warnings[row['cin']]=row
def subtract(stats,year):
    for item in stats['groups']['trends']:
        if item['label']==year:
            assert item['count']>0;item['count']-=1;break
    else:raise ValueError('Missing source-year aggregate for '+year)
for row in warnings.values():
    for stats in [catalog['stats'],catalog['states'][row['state']]['stats'],catalog['industries'][row['industry']],
                  catalog['facets']['class'][row['class']],catalog['facets']['status'][row['status']],catalog['facets']['effective_listing'][row['effective_listing']]]:
        subtract(stats,row['incorporated'][:4])
all_stats=[catalog['stats']]+[item['stats'] for item in catalog['states'].values()]+list(catalog['industries'].values())+[item for groups in catalog['facets'].values() for item in groups.values()]
for stats in all_stats:
    stats['groups']['trends']=[item for item in stats['groups']['trends'] if item['count']]
    stats['summary']['incorporation_date_coverage']=sum(item['count'] for item in stats['groups']['trends'])
catalog['date_quality']={cin:row['incorporated'] for cin,row in warnings.items()}
catalog['date_quality_policy']='The placeholder-looking source date 1111-11-11 and dates beyond the snapshot label are preserved but withheld from incorporation trends, date filters and age scoring. No corrected date is inferred.'
catalog['date_quality_applied']=True
catalog['datasets'][0]['provenance']+=f" {len(warnings):,} implausible source dates are retained in profiles but withheld from date-based analyses."
assert catalog['stats']['summary']['incorporation_date_coverage']==catalog['record_count']-len(warnings)
path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f'Flagged {len(warnings):,} source dates; company counts unchanged; no compressed source chunks modified.')
