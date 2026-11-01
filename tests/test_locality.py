"""City labels must come from a consistent source-address tail, not street text."""
import json,subprocess
from pathlib import Path
import pytest
from intelligence.locality import derive

CASES=[
 ('123 Mumbai Road,PUNE,Pune,Maharashtra,411001-India','Maharashtra','411001','Pune'),
 ('Office,Delhi,Delhi,Delhi,110001-India','Delhi','110001','Delhi'),
 ('Office,Chandigarh,Chandigarh,Chandigarh,160001-India','Chandigarh','160001','Chandigarh'),
 ('Office,Raipur,Raipur,Chattisgarh,492001-India','Chhattisgarh','492001','Raipur'),
 ('Office,Pondicherry,Pondicherry,Pondicherry,605001-India','Puducherry','605001','Pondicherry'),
 ('Office,Pune,Pune,Maharashtra,411001-India','Maharashtra','411002',None),
 ('Office,Pune,Pune,Gujarat,411001-India','Maharashtra','411001',None),
 ('Office,Pune Road,Pune,Maharashtra,411001-India','Maharashtra','411001',None),
 ('Mumbai Road Maharashtra','Maharashtra','411001',None),
 ('Office,NA,Pune,Maharashtra,411001-India','Maharashtra','411001',None),
]
@pytest.mark.parametrize('address,state,pin,expected',CASES)
def test_conservative_locality(address,state,pin,expected):
    assert derive(address,state,pin)==expected

def test_browser_parser_matches_python():
    script="global.self=global;require('./intelligence/static/locality.js');const rows="+json.dumps(CASES)+";console.log(JSON.stringify(rows.map(([address,state,postal_code])=>AtlasLocality.derive({address,state,postal_code}))));"
    actual=json.loads(subprocess.check_output(['node','-e',script],cwd=Path(__file__).resolve().parents[1]))
    assert actual==[case[3] for case in CASES]
