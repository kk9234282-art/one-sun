"""Precompute common class/status/listing views without enlarging data chunks."""
import json
from pathlib import Path
import sqlite3
import sys
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_online_india import Stats

path=Path('deployment/national/catalog.json');catalog=json.loads(path.read_text())
facets={key:defaultdict(Stats) for key in ['class','status','effective_listing']}
with sqlite3.connect('instance/india-online.sqlite') as db:
    for n,(payload,) in enumerate(db.execute('SELECT payload FROM records'),1):
        row=json.loads(payload)
        for field,groups in facets.items():groups[row[field] or 'Unknown'].add(row)
        if n%1000000==0:print('Precomputed common views:',n,flush=True)
catalog['facets']={field:{label:stats.output() for label,stats in groups.items()} for field,groups in facets.items()}
for groups in catalog['facets'].values():assert sum(stats['summary']['companies'] for stats in groups.values())==catalog['record_count']
path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('Common class/status/listing summaries added; no data chunks changed.',flush=True)
