"""Parse only freely shown, dated operating-revenue ranges on public profiles."""
import math,re
from datetime import datetime,date
from decimal import Decimal
from html.parser import HTMLParser

class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,text):
        if not self.skip:self.parts.append(text)

def extract(html,*,cin,company_name,source_url,observed_on):
    parser=Text();parser.feed(html);text=' '.join(' '.join(parser.parts).split())
    identity=re.search(r'Identification Number \(CIN\) of\s+(.{1,250}?)\s+is\s+([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})',text,re.I)
    if not identity or identity[2].upper()!=cin:raise ValueError('Primary profile CIN does not match master')
    match=re.search(r'operating revenue range is\s+(.{1,100}?)\s+for the financial year ending on\s+(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})',text,re.I)
    if not match:raise ValueError('No freely shown dated operating revenue range')
    period=datetime.strptime(match[2].replace(',',''),'%d %B %Y').date()
    if period>date.fromisoformat(observed_on):raise ValueError('Future financial period')
    claim=match[1]
    if not re.search(r'\bINR\b|₹',claim) or re.search(r'\b(?:USD|EUR|GBP|JPY|AUD|CAD)\b',claim):raise ValueError('Unrecognized revenue currency')
    numbers=re.findall(r'(\d[\d,]*(?:\.\d+)?)\s*(cr(?:ore)?s?|lakh?s?|lakhs?|million|billion)',claim,re.I)
    def amount(number,unit):
        unit=unit.lower();scale=10000000 if unit.startswith('cr') else 100000 if unit.startswith('la') else 1000000 if unit=='million' else 1000000000
        value=float(Decimal(number.replace(',',''))*scale)
        if not math.isfinite(value):raise ValueError('Non-finite revenue bound')
        return value
    minimum=maximum=None
    if len(numbers)==2 and re.search(r'[-–]|\bto\b',claim,re.I):minimum,maximum=[amount(*n) for n in numbers]
    elif len(numbers)==1 and re.search(r'over|above|more than|greater than',claim,re.I):minimum=amount(*numbers[0])
    elif len(numbers)==1 and re.search(r'under|below|less than|up to|upto',claim,re.I):maximum=amount(*numbers[0])
    else:raise ValueError('Unrecognized public revenue range')
    if minimum is not None and maximum is not None and minimum>maximum:raise ValueError('Reversed revenue range')
    return dict(cin=cin,company_name=company_name,source_company_name=identity[1],revenue_inr=None,revenue_type='range',revenue_min_inr=minimum,revenue_max_inr=maximum,revenue_display=claim,source_label='Operating revenue range',period_end=period.isoformat(),reporting_basis='unspecified',source_url=source_url,observed_on=observed_on,verification_status='unverified',match_basis='Public profile CIN matches master; revenue range not independently verified',confidence='low',precision='Publisher-reported range; no midpoint or exact revenue inferred',notice='Research lead only. This is a public revenue range, not an independently verified financial statement. Excluded from verified financials, revenue filters, growth and scores.')
