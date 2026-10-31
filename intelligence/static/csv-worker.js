/* Parse user-selected CSV locally in a worker. No network or executable input. */
'use strict';
class CSVStream {
  constructor(onRow) { this.onRow=onRow;this.field='';this.row=[];this.quoted=false;this.pendingQuote=false;this.skipLF=false;this.start=true; }
  emitField() { this.row.push(this.field);this.field=''; }
  emitRow() { this.emitField();if(this.row.some(value=>value!==''))this.onRow(this.row);this.row=[]; }
  feed(text,final=false) {
    for (const ch of text) {
      if(this.start){this.start=false;if(ch==='\ufeff')continue;}
      if(this.skipLF){this.skipLF=false;if(ch==='\n')continue;}
      if(this.quoted){if(ch==='"'){this.quoted=false;this.pendingQuote=true;}else this.field+=ch;}
      else if(this.pendingQuote&&ch==='"'){this.field+='"';this.quoted=true;this.pendingQuote=false;}
      else {
        if(this.pendingQuote&&![' ',',','\r','\n','\t'].includes(ch))throw Error('Unexpected text after a closing quote.');
        if(this.pendingQuote&&(ch===' '||ch==='\t'))continue;
        this.pendingQuote=false;
        if(ch===',')this.emitField();
        else if(ch==='\r'||ch==='\n'){this.emitRow();if(ch==='\r')this.skipLF=true;}
        else if(ch==='"'){if(this.field!=='')throw Error('Quote inside an unquoted CSV field.');this.quoted=true;}
        else this.field+=ch;
      }
      if(this.field.length>1024*1024)throw Error('A CSV field exceeds 1 MiB; inspect the source file.');
    }
    if(final){if(this.quoted)throw Error('CSV ends inside a quoted field.');if(this.field!==''||this.row.length||this.pendingQuote)this.emitRow();}
  }
}
const fields=['cin','name','class','registered_class','category','subcategory','status','incorporated','address','state','district','industry','nic','roc','postal_code','authorised_capital','paid_up_capital','effective_listing','source_id','as_of'];
const aliases={company_name:'name',company_registration_date:'incorporated',date_of_incorporation:'incorporated',company_category:'category',company_class:'class',listing_status:'effective_listing',authorized_capital:'authorised_capital',paidup_capital:'paid_up_capital',company_roc:'roc',company_address:'address',pin_code:'postal_code',company_state:'state',company_status:'status',company_sub_category:'subcategory',company_industrial_classification:'industry',registered_office_address:'address',state_name:'state'};
const header=value=>{const key=value.trim().toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');return aliases[key]||key;};
const title=value=>value.toLowerCase().replace(/\b[a-z]/g,ch=>ch.toUpperCase());
function isoDate(value) {
  let match=value.match(/^(\d{4})-(\d{2})-(\d{2})$/),y,m,d;
  if(match){[,y,m,d]=match;}else{match=value.match(/^(\d{2})[/-](\d{2})[/-](\d{4})$/);if(!match)throw Error('Invalid registration date; expected YYYY-MM-DD or DD/MM/YYYY.');[,d,m,y]=match;}
  const result=`${y}-${m}-${d}`,date=new Date(result+'T00:00:00Z');
  if(!Number.isFinite(date.valueOf())||date.toISOString().slice(0,10)!==result)throw Error('Invalid calendar date.');
  return result;
}
function normalize(values,names,asOf) {
  if(values.length!==names.length)throw Error('CSV column count differs from header.');
  const row={};names.forEach((key,i)=>{const value=values[i].trim();if(value&&!['na','n/a','null','none','-'].includes(value.toLowerCase()))row[key]=value;});
  if(!row.cin||!row.name)throw Error('Missing CIN or company name.');
  row.cin=row.cin.toUpperCase();
  if(!/^[LU]\d{5}[A-Z]{2}\d{4}(PLC|PTC|OPC|NPL|GAP|SGC|GOI|FLC|FTC|ULL|ULT)\d{6}$/.test(row.cin))throw Error('Nonstandard CIN structure; preserved as an exception.');
  if(row.class){row.registered_class=row.registered_class||row.class;const mapping={'private':'Private','public':'Public','private limited':'Private','public limited':'Public','one person company':'Private'};row.class=mapping[row.class.toLowerCase()];if(!row.class)throw Error('Unsupported company class.');}
  if(row.incorporated)row.incorporated=isoDate(row.incorporated);
  for(const key of ['authorised_capital','paid_up_capital'])if(row[key]!=null){const text=row[key].replaceAll(',','');if(!/^\+?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(text))throw Error('Invalid '+key);const amount=Number(text);if(!Number.isFinite(amount)||amount<0||amount>Number.MAX_SAFE_INTEGER)throw Error('Capital is negative, non-finite or too large for precise browser representation.');row[key]=amount;}
  if(row.effective_listing){row.effective_listing=row.effective_listing.toLowerCase();if(!['listed','unlisted','unknown'].includes(row.effective_listing))throw Error('Invalid listing status.');}else row.effective_listing=null;
  if(row.status)row.status=title(row.status);if(row.state)row.state=title(row.state);
  row.source_id='user_upload';row.as_of=asOf;
  return fields.map(key=>row[key]??null);
}
self.AtlasCSV={CSVStream,normalize,fields,header};
self.onmessage=async event=>{
  const {file,asOf}=event.data;
  let names=null,originalHeaders=null,record=0,accepted=0,rejected=0,rows=[],exceptions=[];
  const flush=()=>{if(rows.length||exceptions.length){self.postMessage({type:'batch',rows,exceptions});rows=[];exceptions=[];}};
  try {
    isoDate(asOf);if(asOf>new Date().toISOString().slice(0,10))throw Error('Snapshot date cannot be in the future.');
    const parser=new CSVStream(values=>{
      record++;
      if(!names){originalHeaders=values;names=values.map(header);if(new Set(names).size!==names.length)throw Error('Duplicate normalized headers.');if(!names.includes('cin')||!names.includes('name'))throw Error('The CSV must include CIN and Company Name columns.');self.postMessage({type:'headers',headers:originalHeaders,fields});return;}
      try{rows.push(normalize(values,names,asOf));accepted++;}catch(error){exceptions.push({record,reason:error.message,values});rejected++;}
      if(rows.length+exceptions.length>=1000)flush();
    });
    const reader=file.stream().getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0;
    while(true){const {value,done}=await reader.read();if(done)break;bytes+=value.byteLength;parser.feed(decoder.decode(value,{stream:true}));self.postMessage({type:'progress',bytes,total:file.size,accepted,rejected});}
    parser.feed(decoder.decode(),true);flush();
    if(!names||accepted===0)throw Error('No structurally valid company rows found.');
    self.postMessage({type:'complete',accepted,rejected,records:record-1});
  } catch(error){self.postMessage({type:'error',message:error.message});}
};
