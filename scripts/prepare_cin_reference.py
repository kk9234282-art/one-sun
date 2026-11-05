"""Prepare version-labelled NIC reference candidates; never infer a company's edition."""
import argparse,hashlib,json,re
from pathlib import Path
SOURCES={
 '2004':{'authority':'MOSPI NIC 2004 detailed structure; public PDF mirror','url':'http://mospi.nic.in/sites/default/files/main_menu/national_industrial_classification/nic_2004_struc_detail.pdf','mirror_url':'https://github.com/matcdac/CorporateIndiaDataSourceXLSX/blob/cca5f086d19e8337a09641ba8df7fe997d075af7/understanding-metadata/nic_2004_struc_detail.pdf','input_sha256':'fb68d9511d257402d2d65db0ef1581ba85f0fce47ed5f4bf43bc11217b8505ca'},
 '2008':{'authority':'MOSPI NIC 2008; third-party transcription','url':'https://www.mospi.gov.in/sites/default/files/main_menu/national_product_classification/NIC_2008.xlsx','mirror_url':'https://github.com/colaberry/WorldOfTaxonomy/blob/62f31df232fb38a0c2da5dac2068f30dc04d3618/frontend/public/llms-codes/nic_2008.txt','input_sha256':'2d032d0b7b1d9d308cf3a7d0961e124c3606933ae47dae9d2e3db9a4457ac10e'},
}
def parse_2004(text):
    found={};current=None;lines=text.splitlines()
    for i,line in enumerate(lines):
        line=line.replace('\f','')
        m=re.match(r'^\s*((?:\d{3,5}\s+){1,3})(\S.*)$',line)
        if m and len(line)-len(line.lstrip())<=20:
            codes=m[1].split();title=m[2].strip()
            if len(codes[-1])==5 and i+1<len(lines) and re.match(r'\s*\([A-Z]\)(?:\s|$)',lines[i+1]):current=None;continue
            current=codes[-1]
            for code in codes:
                if code in found:raise ValueError('Duplicate reference code '+code)
                found[code]=title
        elif current and re.match(r'^\s{20,}\S',line) and not re.match(r'^\s*(?:Description|Class|Sub-|Group|SECTION|DIVISION)',line):found[current]+=' '+line.strip()
        elif re.match(r'^\s*(?:SECTION|DIVISION)',line):current=None
    return found

def parse_2008(text):
    return {m[1]:m[2].split(' -- ',1)[0].strip() for m in re.finditer(r'^\[(\d{3,5})\]\s+(.+)$',text,re.M)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--nic2004-pdf',required=True);p.add_argument('--nic2004-text',required=True);p.add_argument('--nic2008-text',required=True);p.add_argument('--output',default='intelligence/data/cin-activity-reference.json');a=p.parse_args()
    for edition,path in [('2004',a.nic2004_pdf),('2008',a.nic2008_text)]:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=SOURCES[edition]['input_sha256']:raise ValueError('Reference input changed; review source '+edition)
    refs={'2004':parse_2004(Path(a.nic2004_text).read_text()),'2008':parse_2008(Path(a.nic2008_text).read_text())}
    assert sum(len(k)==5 for k in refs['2004'])==1184
    assert sum(len(k)==5 for k in refs['2008'])==1304
    assert refs['2004']['15511']=='Manufacture of country liquor'
    assert refs['2008']['01111']=='Growing of wheat'
    out=Path(a.output);out.parent.mkdir(exist_ok=True);out.write_text(json.dumps({'schema_version':1,'sources':SOURCES,'references':refs},ensure_ascii=False,separators=(',',':'))+'\n')
    print('Prepared reference entries:',{edition:len(rows) for edition,rows in refs.items()})
if __name__=='__main__':main()
