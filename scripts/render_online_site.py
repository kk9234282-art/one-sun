"""Render the shared national site's HTML without touching private data stores."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import Flask,g,render_template

root=Path(__file__).resolve().parents[1]
app=Flask(__name__,template_folder=str(root/'intelligence/templates'),static_folder=str(root/'intelligence/static'),static_url_path='/static')
with app.test_request_context('/'):
    g.user={'username':'Online visitor','role':'public'}
    (root/'deployment/index.html').write_text(render_template('index.html',sources={},public_snapshot=True,online_catalog='/national/catalog.json'),encoding='utf-8')
print('Rendered national online entry point; no account data or session keys emitted.')
