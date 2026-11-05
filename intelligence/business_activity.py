"""Source-described business activities. CIN codes are preserved, never version-guessed."""
import gzip,json,re
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

# Tags describe words in source activity text, not inference from a company name.
TAG_PATTERNS={
 'Alcoholic beverages':r'\b(?:liquor|alcoholic beverages?|alcoholic spirits|potable alcohol|brewer(?:y|ies)|beer|wines?|whisky|whiskey|vodka|rum)\b',
 'Agriculture and farming':r'\b(?:agriculture|agricultural|farming|crop cultivation|horticulture|plantations?|crop nutrition|crop protection|soil health management|agri.inputs?|seeds|seed (?:production|processing|distribution|marketing|selling|business)|agrochemicals?|fertili[sz]ers?|pesticides?)\b',
 'Food and ingredients':r'\b(?:food|foods|flour|rice|edible oils?|spices?|ingredients|sugar|dairy|snacks?)\b',
 'Non-alcoholic beverages':r'\b(?:soft drinks?|bottled water|fruit juice|tea|coffee|non.alcoholic)\b',
 'Pharmaceuticals':r'\b(?:pharmaceuticals?|pharma|medicines?|bulk drugs?|drug formulations?|active pharmaceutical ingredients?|gelatin capsules?|HPMC capsules?)\b',
 'Healthcare and diagnostics':r'\b(?:healthcare|hospitals?|diagnostics?|medical devices?|clinics?|pathology)\b',
 'Software and IT services':r'\b(?:software|information technology|IT services|SaaS|cybersecurity|cloud computing|IT consulting|IT.enabled services)\b',
 'Financial services and lending':r'\b(?:financial services|lending|loans?|NBFC|microfinance|non.banking financial)\b',
 'Banking':r'\b(?:banking|commercial bank|private sector bank|public sector bank)\b',
 'Insurance':r'\b(?:insurance|reinsurance|insurer)\b',
 'Investment and stockbroking':r'\b(?:stockbrok(?:ing|er)|securities brok(?:ing|er)|asset management|investment banking|mutual funds?|portfolio management)\b',
 'Real estate':r'\b(?:real estate|property development|residential projects?|commercial properties)\b',
 'Construction and infrastructure':r'\b(?:construction|infrastructur(?:e|al)|railway electrification|turnkey OHE|EPC|civil engineering|road projects?)\b',
 'Renewable energy':r'\b(?:renewable|solar|wind energy|wind power|hydropower)\b',
 'Electricity and utilities':r'\b(?:power generation|power transmission|power distribution|electricity|electric utilities)\b',
 'Oil and gas':r'\b(?:oil and gas|natural gas|petroleum|crude oil|oil refining|LPG|LNG)\b',
 'Chemicals':r'\b(?:chemicals?|petrochemicals?|dyes|pigments?|resins?|denatured spirits|industrial alcohol|ethanol)\b',
 'Textiles and apparel':r'\b(?:textiles?|garments?|apparel|yarn|fabrics?|spinning|weaving|knitwear|clothing|western[ -]wear|ethnic wear|men[’\']s[ -]wear)\b',
 'Automobiles and components':r'\b(?:automobiles?|automotive|auto components?|motor vehicles?|two.wheelers?|passenger vehicles?)\b',
 'Engineering and machinery':r'\b(?:machiner(?:y|ies)|special.purpose machines|carbide tools|hydraulics|machine tools?|industrial equipment|engineering products|pumps?|compressors?)\b',
 'Electrical equipment':r'\b(?:electrical equipment|transformers?|cables?|wires?|switchgear|electric motors?|LED lights?|LED lighting|LED products?)\b',
 'Electronics and semiconductors':r'\b(?:electronics?|semiconductors?|printed circuit boards?|PCBs?|POS devices?|printers?|keyboards?)\b',
 'Metals and mining':r'\b(?:mining|steel|aluminium|aluminum|copper|zinc|iron ore|sponge iron|ferro.alloys?|ferro.?chrome|TMT bars?|galvanized iron|GI pipes|ERW.{0,15}pipes|SAW pipes)\b',
 'Cement and building materials':r'\b(?:cement|building materials?|tiles|ceramics?|plywood|laminates?)\b',
 'Transport and logistics':r'\b(?:logistics|freight|transportation|shipping|warehousing|courier|supply chain|transporters?)\b',
 'Aviation':r'\b(?:aviation|airlines?|airports?|air transport)\b',
 'Retail and distribution':r'\b(?:retail|retailing|trading|trades|wholesale|distribution|distributors?|e.commerce)\b',
 'Hotels and hospitality':r'\b(?:hotels?|hoteliering|hoteliers?|hospitality|resorts?|restaurants?|catering)\b',
 'Travel and tourism':r'\b(?:tourism|travel services|travel agency|tour operators?)\b',
 'Telecommunications':r'\b(?:telecommunications?|telecom|broadband|internet service providers?)\b',
 'Media and entertainment':r'\b(?:media|entertainment|broadcasting|television|film production|cinemas?|publishing|radio broad[ -]?cast|print services)\b',
 'Education and training':r'\b(?:education|educational|vocational|training services|e.learning)\b',
 'Paper and packaging':r'\b(?:paper|packaging|corrugated|cartons?|paperboard)\b',
 'Plastics and rubber':r'\b(?:plastics?|polymers?|rubber|tyres?|tires?|poly\s*iso\s*butylene|PET (?:jars?|bottles?))\b',
 'Gems and jewellery':r'\b(?:jewellery|jewelry|diamonds?|gemstones?|gems)\b',
 'Defence and aerospace':r'\b(?:defence|defense|aerospace|military)\b',
 'Water and waste management':r'\b(?:water treatment|waste management|wastewater|recycling|sewage)\b',
 'Wood and plywood products':r'\b(?:wood[ -]based products?|plywood|decorative laminates?|veneers?|timber)\b',
 'Poultry and egg products':r'\b(?:poultry|eggs?|egg products?)\b',
 'Aquaculture and seafood':r'\b(?:aquaculture|shrimps?|fish farming|seafood|marine products?)\b',
 'Animal feed':r'\b(?:(?:animal|poultry|shrimp|fish|cattle) feeds?|animal nutrition)\b',
 'Agricultural inputs and seeds':r'\b(?:agri.inputs?|crop nutrition|crop protection|soil health management|seeds|seed (?:production|processing|distribution|marketing|selling|business)|fertili[sz]ers?|pesticides?|agrochemicals?)\b',
 'Investment and holding companies':r'\b(?:investment compan(?:y|ies)|holding compan(?:y|ies))\b',
 'Fashion accessories and bags':r'\b(?:fashion accessories|fashion bags|backpacks)\b',
 'Lubricants and petroleum products':r'\b(?:lubricants?|lubricating oils?|base oils?|fuel oils?|bitumen|rubber process oils?)\b',
 'Business and professional services':r'\b(?:consultancy|consulting|professional services|business process|BPO|staffing|recruitment)\b',
}
TAG_RULE_VERSION=2
TAG_POLICY='Source-text research topics, not confirmed operating roles. Leading legal names, plantation commodities and selected customer-use phrases are excluded from downstream product tags. Identity evidence, descriptions and CIN candidates are preserved.'

class AboutParser(HTMLParser):
    def __init__(self):
        super().__init__();self.depth=0;self.parts=[];self.skip=0;self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if self.depth:
            if tag not in ('br','hr','img','input','meta','link','source','wbr'):self.depth+=1
            if tag=='sup':self.skip+=1
        elif tag=='div' and 'about' in a.get('class','').split():self.depth=1
    def handle_endtag(self,tag):
        if self.depth:
            if tag=='sup':self.skip=max(0,self.skip-1)
            self.depth-=1
    def handle_data(self,data):
        if self.depth and not self.skip:self.parts.append(data)

def extract_description(html,symbol):
    parser=AboutParser();parser.feed(html)
    symbols={parse_qs(urlsplit(u).query).get('symbol',[''])[0].upper() for u in parser.links if urlsplit(u).hostname=='www.nseindia.com'}
    if symbol.upper() not in symbols:raise ValueError('Page NSE symbol mismatch')
    text=' '.join(' '.join(parser.parts).split())
    if len(text)<25:raise ValueError('No usable public About description')
    if len(text)>4000:raise ValueError('Description exceeds review limit')
    return text

def tags_for(text):
    # Drop the leading legal company name so names do not become product evidence.
    name=re.match(r'^(?:Incorporated in \d{4},?\s*)?[^.;\n]{0,160}?\b(?:Limited|Ltd)\.?\s+',text,re.I)
    business=text[name.end():] if name else text
    # Crop production and customer-use phrases do not establish downstream manufacture.
    plantation=r'\b(?:plantations?|growing|cultivation|farming)\s+(?:of\s+)?(?:the\s+)?(?:tea|coffee|rubber)(?:\s+(?:and|&)\s+(?:tea|coffee|rubber))*\b|\b(?:tea|coffee|rubber)(?:\s+(?:and|&)\s+(?:tea|coffee|rubber))*\s+(?:trees?|plantations?|farming|cultivation)\b'
    downstream=re.sub(plantation,' ',business,flags=re.I)
    downstream=re.sub(r'\b(?:automotive|automobile|rubber)[ -]+(?:process[ -]+)?(?=lubricants?\b|oils?\b|fluids?\b|coatings?\b|paints?\b|adhesives?\b)','',downstream,flags=re.I)
    downstream=re.sub(r'\b(?:for|used by|used in|serving|supplied to)\s+(?:the\s+)?(?:automotive|automobile|rubber|plywood|poultry|aquaculture)(?:[ -]+industr(?:y|ies))?\b',' ',downstream,flags=re.I)
    context_tags={'Non-alcoholic beverages','Plastics and rubber','Automobiles and components','Wood and plywood products','Poultry and egg products','Aquaculture and seafood'}
    tags=[tag for tag,pattern in TAG_PATTERNS.items() if re.search(pattern,downstream if tag in context_tags else business,re.I)]
    # Explicit parts plus automotive context can survive customer-context masking.
    if 'Automobiles and components' not in tags and re.search(r'\b(?:automotive|vehicles?|engines?)\b',business,re.I) and re.search(r'\b(?:piston rings?|differential gears?|crank pins?|fuel management systems?|seating systems?|interior components?)\b',business,re.I):tags.append('Automobiles and components')
    if 'Pharmaceuticals' not in tags and re.search(r'\bAPIs?\b.{0,40}\bformulations?\b',business,re.I):tags.append('Pharmaceuticals')
    if re.search(r'\bmanufactur(?:e|es|ing)\b.{0,100}\balcohol\b',business,re.I) and not re.search(r'\b(?:industrial|denatured|potable|ethyl) alcohol\b|\bethanol\b',business,re.I) and 'Alcoholic beverages' not in tags:
        tags.append('Alcohol products (type unspecified)')
    return tags


@lru_cache(maxsize=1)
def dataset():
    root=Path(__file__).parent/'static';manifest=root/'business-activity-manifest.json'
    if not manifest.exists():return {'records':[],'report':{}}
    descriptor=json.loads(manifest.read_text());body=(root/Path(descriptor['path']).name).read_bytes()
    import hashlib
    if hashlib.sha256(body).hexdigest()!=descriptor['sha256']:raise ValueError('Business activity checksum mismatch')
    return json.loads(gzip.decompress(body))[0]

@lru_cache(maxsize=1)
def records():return {r['cin']:r for r in dataset()['records']}

def enrich(row):
    from .registered_activity import details
    row.update(details(row['cin']))
    from .review_flags import flag_for
    row['activity_review_flag']=flag_for(row['cin'])
    entry=records().get(row['cin']);row.update(registered_activity_code=row['cin'][1:6],business_description=entry['description'] if entry else None,business_tags=entry['tags'] if entry else [],activity_evidence=entry['identity_status'] if entry else 'needs_research',activity_source=entry['source_url'] if entry else None,activity_observed_on=entry['observed_on'] if entry else None,activity_identity_source=entry.get('identity_source_url') if entry else None)
    return row

def matches(cin,tag,evidence,query):
    r=records().get(cin)
    if evidence=='needs_research':return int(r is None and not tag and not query)
    if not r:return int(not(tag or evidence or query))
    return int((not tag or tag in r['tags']) and (not evidence or evidence=='source_described' or evidence==r['identity_status']) and (not query or query.casefold() in r['description'].casefold()))
