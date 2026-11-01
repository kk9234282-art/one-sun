"""Postal district lookup must depend only on structured state/PIN, never address/ROC."""
import json,subprocess
from pathlib import Path
import pytest
from intelligence.locality import derive,reference

CASES=[
 ('411001','Maharashtra','Pune'),
 ('411002','Maharashtra','Pune'),
 ('400001','Maharashtra','Mumbai'),
 ('421401','Maharashtra','Thane'),
 ('110001','Delhi','New Delhi'),
 ('560001','Karnataka','Bengaluru Urban'),
 ('411001','Gujarat',None),
 ('000000','Maharashtra',None),
 ('999999','Maharashtra',None),
 ('41100','Maharashtra',None),
 (None,'Maharashtra',None),
]
@pytest.mark.parametrize('pin,state,expected',CASES)
def test_pin_district(pin,state,expected):
    assert derive(pin,state)==expected

def test_ambiguous_pin_withheld():
    assert reference()['ambiguous_pairs']>0
    # Conflicting postal districts are not resolved from company addresses or ROC.
    assert derive('110003','Delhi') is None

def test_browser_parser_matches_python_and_ignores_address_roc():
    script="""global.self=global;global.fetch=async()=>({ok:true,json:async()=>require('./intelligence/static/pin-districts.json')});require('./intelligence/static/locality.js');
    (async()=>{await AtlasLocality.ready;const rows="""+json.dumps(CASES)+""";console.log(JSON.stringify(rows.map(([postal_code,state])=>AtlasLocality.derive({postal_code,state,address:'Wrong City,Wrong District,Gujarat,999999',roc:'ROC Ahmedabad'}))));})().catch(error=>{console.error(error);process.exit(1)});"""
    actual=json.loads(subprocess.check_output(['node','-e',script],cwd=Path(__file__).resolve().parents[1]))
    assert actual==[case[2] for case in CASES]
