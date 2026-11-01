"""Postal district lookup from source PIN and state; no address parsing."""
import re
import json
from functools import lru_cache
from pathlib import Path

ALIASES={'orissa':'odisha','pondicherry':'puducherry','jammu & kashmir':'jammu and kashmir','dadra & nagar haveli':'dadra and nagar haveli and daman and diu','daman and diu':'dadra and nagar haveli and daman and diu'}
ALIASES.update({'chattisgarh':'chhattisgarh','uttaranchal':'uttarakhand','tamilnadu':'tamil nadu','andaman & nicobar islands':'andaman and nicobar islands','andaman & nicobar':'andaman and nicobar islands','dadra and nagar haveli':'dadra and nagar haveli and daman and diu','nct of delhi':'delhi','n.c.t. of delhi':'delhi'})
ALIASES['the dadra and nagar haveli and daman and diu']='dadra and nagar haveli and daman and diu'

def canonical(value):
    value=' '.join(str(value or '').split()).lower()
    return ALIASES.get(value,value)


@lru_cache(maxsize=1)
def reference():
    return json.loads((Path(__file__).parent/'static/pin-districts.json').read_text())

def derive(postal_code,state):
    """Look up a postal district using only source PIN/state; never read an address or ROC."""
    pin=str(postal_code or '').strip()
    if not re.fullmatch(r'[1-9][0-9]{5}',pin):return None
    return reference()['states'].get(canonical(state),{}).get(pin)
