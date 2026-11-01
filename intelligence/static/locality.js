/* Only the literal locality in a consistent address tail; never infer from ROC/PIN. */
'use strict';
(() => {
  const aliases={'orissa':'odisha','pondicherry':'puducherry','jammu & kashmir':'jammu and kashmir','dadra & nagar haveli':'dadra and nagar haveli and daman and diu','daman and diu':'dadra and nagar haveli and daman and diu'};
  Object.assign(aliases,{'chattisgarh':'chhattisgarh','uttaranchal':'uttarakhand','tamilnadu':'tamil nadu','andaman & nicobar islands':'andaman and nicobar islands','andaman & nicobar':'andaman and nicobar islands','dadra and nagar haveli':'dadra and nagar haveli and daman and diu','nct of delhi':'delhi','n.c.t. of delhi':'delhi'});
  const cityStates=new Set(['delhi','chandigarh','puducherry']);
  const empty=new Set(['na','n/a','nil','unknown','none','not available','not applicable','india','city','district','east','west','north','south']);
  const canonical=value=>{const text=String(value||'').trim().replace(/\s+/g,' ').toLowerCase();return aliases[text]||text;};
  const place=value=>{const text=value.trim().replace(/\s+/g,' ');if(text.length<2||text.length>60||!/^[A-Za-z .&'()/\-]+$/.test(text)||empty.has(canonical(text))||/\b(road|floor|flat|plot|house|building|sector|survey|block|street|hno|shop|office|tower|premises|lane)\b/i.test(text))return null;return text.toLowerCase().replace(/\b[a-z]/g,ch=>ch.toUpperCase());};
  const derive=row=>{const parts=String(row.address||'').split(',').map(value=>value.trim());if(parts.length<4)return null;const pin=parts.at(-1).match(/^(\d{6})(?:\s*-\s*India)?$/i);if(!pin||pin[1]==='000000'||pin[1]!==String(row.postal_code||'')||!canonical(row.state)||canonical(parts.at(-2))!==canonical(row.state))return null;const city=place(parts.at(-4)),district=place(parts.at(-3));if(!city||!district)return null;if(!cityStates.has(canonical(row.state))&&(canonical(city)===canonical(row.state)||canonical(district)===canonical(row.state)))return null;return city;};
  const api={derive,canonical};
  if(typeof window!=='undefined')window.AtlasLocality=api;
  else self.AtlasLocality=api;
})();
