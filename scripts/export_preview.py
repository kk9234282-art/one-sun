"""Export a data-free styled preview, or an explicitly requested private snapshot."""
import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence import create_app
from intelligence.db import get_db
from intelligence.analytics import directory,overview

esc=lambda value:html.escape(str(value if value is not None else 'Unknown'),quote=True)
num=lambda value:f'{value:,}' if isinstance(value,int) else esc(value)


def bars(rows):
    maximum=max((r['count'] for r in rows),default=1)
    return ''.join(f'<div class="bar-row"><span class="bar-label" title="{esc(r["label"])}">{esc(r["label"])}</span><div class="bar-track"><div class="bar-fill" style="width:{r["count"]/maximum*100:.2f}%"></div></div><span class="bar-value">{num(r["count"])}</span></div>' for r in rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-data',action='store_true',help='Write an ignored local snapshot containing database records')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    fields=('companies','active','inactive','other_status','private','public','listed','unlisted')
    data={'summary':dict.fromkeys(fields),'groups':dict.fromkeys(('state','industry','class','status','effective_listing','trends'),[]),'datasets':[]}
    records=[]
    if args.include_data:
        app=create_app()
        with app.app_context():
            data=overview(get_db(),{})
            records=directory(get_db(),{'per_page':'50'})['rows']
    s=data['summary'];groups=data['groups']
    css=(root/'intelligence/static/app.css').read_text()
    cards=[('Imported companies','companies'),('Active','active'),('Inactive / closed','inactive'),('Other status','other_status'),
           ('Private incl. OPC','private'),('Public','public'),('Marked listed','listed'),('Marked unlisted','unlisted')]
    caption='Within imported coverage' if args.include_data else 'No data bundled'
    metrics=''.join(f'<article class="metric"><span class="metric-label">{label}</span><strong class="number">{num(s[key])}</strong><small>{caption}</small></article>' for label,key in cards)
    chart_fields=[('State distribution','state'),('Industry composition','industry'),('Company structure','class'),('Registered status','status'),('Listing labels from uploaded file','effective_listing'),('Recent incorporation years','trends')]
    charts=''.join(f'<article class="card"><h3>{title}</h3>{bars(groups[key][-15:] if key=="trends" else groups[key][:14]) if groups[key] else "<div class=empty>Data excluded from this preview.</div>"}</article>' for title,key in chart_fields)
    columns=[('name','Company'),('cin','CIN'),('registered_class','Registered class'),('status','Status'),('state','State'),('incorporated','Incorporated'),('effective_listing','Listing'),('paid_up_capital','Paid-up capital (₹)')]
    headers=''.join(f'<th>{title}</th>' for key,title in columns)
    rows=''.join('<tr>'+''.join(f'<td>{num(row[key]) if key=="paid_up_capital" else esc(row[key])}</td>' for key,title in columns)+'</tr>' for row in records)
    if not records:
        rows=f'<tr><td colspan="{len(columns)}" class="empty">No company records are bundled. Use the full application with a privately configured database.</td></tr>'
    coverage=''.join(f'<p><strong>{esc(d["title"])}</strong><br>{esc(d["scope"])}<br><small>{esc(d["date_basis"])}</small></p>' for d in data['datasets'])
    mode='private-data' if args.include_data else 'code-only'
    heading='Private local data snapshot.' if args.include_data else 'Your corporate intelligence workspace.'
    notice='Private local snapshot containing imported records. Do not publish without authorisation.' if args.include_data else 'Code-only preview. Company records, dataset statistics, reports and screenshots are excluded. Values marked Unknown indicate that no data is bundled, not zero companies.'
    directory_caption=f'First {len(records)} of {num(s["companies"])} imported companies' if args.include_data else 'Data not included in this deployment'
    output=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atlas India — styled data preview</title><style>{css}</style></head>
<body data-publish-mode="{mode}"><aside class="sidebar"><a class="brand" href="#overview">◈ ATLAS <span>INDIA</span></a><p class="eyebrow">CORPORATE INTELLIGENCE</p><nav aria-label="Preview sections"><a class="nav active" href="#overview">◫ Market overview</a><a class="nav" href="#charts">▦ Corporate footprint</a><a class="nav" href="#directory">⌕ Company directory</a></nav><div class="sidebar-foot">Read-only design preview</div></aside>
<div class="workspace"><header class="topbar"><span>Research / <strong>Market overview</strong></span><span class="pill">Embedded CSS · no external assets</span></header><main id="overview"><div class="heading"><div><p class="eyebrow">INDIA CORPORATE INTELLIGENCE</p><h1>The enterprise landscape.</h1><p>{heading}</p></div></div>
<div class="notice"><div><strong>{notice}</strong> This file includes its CSS and works without the Flask server. Authentication, full search, filters, profiles and imports run in the full application.</div></div>
<div class="notice"><div>{coverage}</div></div><section class="metrics">{metrics}</section><section id="charts"><div class="section-heading"><h2>Corporate footprint</h2><span class="muted">Counts from database records · not national totals</span></div><div class="chart-grid">{charts}</div></section>
<section id="directory"><div class="section-heading"><h2>Company directory</h2><span class="muted">{directory_caption}</span></div><div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div></section><footer>ATLAS / INDIA <span>Transparent coverage · no fabricated financial data</span></footer></main></div></body></html>'''
    target=root/'instance/previews/dashboard.html' if args.include_data else root/'preview.html'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(output,encoding='utf-8')
    print(f'Wrote {target}: {target.stat().st_size:,} bytes; mode={mode}; CSS embedded.')


if __name__=='__main__':main()
