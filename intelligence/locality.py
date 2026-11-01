"""Conservative extraction of a supplied address locality, not geocoding."""
import re

ALIASES={'orissa':'odisha','pondicherry':'puducherry','jammu & kashmir':'jammu and kashmir','dadra & nagar haveli':'dadra and nagar haveli and daman and diu','daman and diu':'dadra and nagar haveli and daman and diu'}
ALIASES.update({'chattisgarh':'chhattisgarh','uttaranchal':'uttarakhand','tamilnadu':'tamil nadu','andaman & nicobar islands':'andaman and nicobar islands','andaman & nicobar':'andaman and nicobar islands','dadra and nagar haveli':'dadra and nagar haveli and daman and diu','nct of delhi':'delhi','n.c.t. of delhi':'delhi'})
CITY_STATES={'delhi','chandigarh','puducherry'}
EMPTY={'na','n/a','nil','unknown','none','not available','not applicable','india','city','district','east','west','north','south'}
def canonical(value):
    value=' '.join(str(value or '').split()).lower()
    return ALIASES.get(value,value)
def place(value):
    value=' '.join(value.split())
    if not 2<=len(value)<=60 or not re.fullmatch(r"[A-Za-z .&'()/\-]+",value):return None
    if canonical(value) in EMPTY:return None
    if re.search(r'\b(road|floor|flat|plot|house|building|sector|survey|block|street|hno|shop|office|tower|premises|lane)\b',value,re.I):return None
    return value.title()
def derive(address,state,postal_code):
    parts=[part.strip() for part in str(address or '').split(',')]
    if len(parts)<4:return None
    pin=re.fullmatch(r'(\d{6})(?:\s*-\s*India)?',parts[-1],re.I)
    if not pin or pin[1]=='000000' or pin[1]!=str(postal_code or ''):return None
    if not canonical(state) or canonical(parts[-2])!=canonical(state):return None
    city,district=place(parts[-4]),place(parts[-3])
    if not city or not district:return None
    if canonical(state) not in CITY_STATES and (canonical(city)==canonical(state) or canonical(district)==canonical(state)):return None
    return city
