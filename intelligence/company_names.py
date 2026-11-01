"""Conservative legal-name keys for candidate discovery, never identity proof."""
import re,unicodedata

def candidate_key(value):
    name=unicodedata.normalize('NFKC',value).upper()
    name=re.sub(r'\bLTD\b','LIMITED',name)
    return re.sub(r'[^A-Z0-9]','',name)

def discover_variants(companies,exchange,covered):
    names={};exact=set()
    for row in companies:
        if row['status']!='Active' or row['effective_listing']!='listed':continue
        exact.add(row['name'].upper());names.setdefault(candidate_key(row['name']),[]).append(row)
    result=[]
    for issuer in exchange:
        matches=names.get(candidate_key(issuer['NAME OF COMPANY']),[])
        if issuer['NAME OF COMPANY'].upper() not in exact and len(matches)==1 and matches[0]['cin'] not in covered:
            result.append({'symbol':issuer['SYMBOL'],'cin':matches[0]['cin'],'master_name':matches[0]['name'],'exchange_name':issuer['NAME OF COMPANY']})
    return result
