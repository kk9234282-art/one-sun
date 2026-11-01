"""Read public annual Screener tables; identity must be independently verified by CIN."""
import calendar,re
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlsplit,parse_qs

class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.sections={};self.active=None;self.depth=0;self.row=None;self.cell=None;self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href'):self.links.append(attrs['href'])
        if tag=='section':self.active=attrs.get('id');self.sections.setdefault(self.active,{'text':[],'rows':[]})
        if not self.active:return
        if tag=='table':self.depth+=1
        if self.depth and tag=='tr':self.row=[]
        if self.row is not None and tag in ('td','th'):self.cell={'text':[],'date':attrs.get('data-date-key')}
    def handle_data(self,text):
        if self.active:self.sections[self.active]['text'].append(text)
        if self.cell is not None:self.cell['text'].append(text)
    def handle_endtag(self,tag):
        if self.cell is not None and tag in ('td','th'):
            self.cell['text']=' '.join(' '.join(self.cell['text']).split());self.row.append(self.cell);self.cell=None
        if tag=='tr' and self.row is not None:
            if self.active:self.sections[self.active]['rows'].append(self.row)
            self.row=None
        if tag=='table':self.depth=max(0,self.depth-1)
        if tag=='section':self.active=None

def parse_annual(html,*,cin,symbol,year,published,source_url,identity_url,retrieved):
    parser=Tables();parser.feed(html)
    symbols={parse_qs(urlsplit(link).query).get('symbol',[''])[0].upper() for link in parser.links if urlsplit(link).hostname=='www.nseindia.com'}
    if symbol.upper() not in symbols:raise ValueError('Screener NSE symbol does not match independently verified issuer')
    section=parser.sections.get('profit-loss')
    if not section:raise ValueError('No public annual profit/loss table')
    heading=' '.join(section['text'][:40]);basis='consolidated' if '/consolidated/' in source_url else 'standalone'
    if not re.search(r'\b'+basis+r'\s+Figures in Rs\. Crores',heading,re.I):raise ValueError('Annual reporting basis or crore unit is not explicit')
    table=section['rows'];headers=next((row for row in table if any(c['date'] for c in row)),None)
    if not headers:raise ValueError('No dated annual headers')
    by_date={cell['date']:i for i,cell in enumerate(headers) if cell['date'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}',cell['date'])}
    facts={}
    for row in table:
        if row:facts[row[0]['text'].replace('+','').strip()]=row
    revenue_label=next((label for label in ['Sales','Revenue'] if label in facts),None)
    if revenue_label is None or 'Net Profit' not in facts:raise ValueError('Supported annual revenue and profit rows are missing')
    def number(label,column):
        row=facts.get(label,[])
        if len(row)<=column:return None
        text=row[column]['text'].replace(',','').replace('−','-').strip()
        if text in ('','-','—'):return None
        if not re.fullmatch(r'-?\d+(?:\.\d+)?',text):raise ValueError('Unrecognized annual numeric value')
        return str(Decimal(text)*10000000)
    output=[]
    for end,column in by_date.items():
        ending=date.fromisoformat(end)
        if ending.year not in (year,year-1):continue
        previous=f'{ending.year-1}-{ending.month:02}-{min(ending.day,calendar.monthrange(ending.year-1,ending.month)[1]):02}'
        if previous not in by_date:continue
        preceding=[(i,period) for period,i in by_date.items() if i<column]
        if not preceding or max(preceding)[1]!=previous:continue
        if end>published:continue
        revenue=number(revenue_label,column);profit=number('Net Profit',column)
        if revenue is None and profit is None:continue
        output.append(dict(cin=cin,financial_year=ending.year,reporting_type=basis,unit='INR',period_end=end,period_months=12,revenue=revenue,revenue_metric='reported_revenue',net_profit=profit,assets=None,liabilities=None,expenses=None,ebitda=None,source_id='screener',source_precision='Public INR crore table; displayed amounts may be rounded',source_url=source_url,as_of=published,identity_source_url=identity_url,source_retrieved_on=retrieved,source_date_basis='NSE annual-report dissemination; financial table retrieved separately'))
    if not any(row['financial_year']==year for row in output):raise ValueError('No supported 12-month annual column for the verified report year')
    return output
