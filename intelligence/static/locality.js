/* Postal district from source state/PIN only. ROC is a separate jurisdiction filter. */
'use strict';
(() => {
  const aliases={'orissa':'odisha','pondicherry':'puducherry','jammu & kashmir':'jammu and kashmir','dadra & nagar haveli':'dadra and nagar haveli and daman and diu','daman and diu':'dadra and nagar haveli and daman and diu'};
  Object.assign(aliases,{'chattisgarh':'chhattisgarh','uttaranchal':'uttarakhand','tamilnadu':'tamil nadu','andaman & nicobar islands':'andaman and nicobar islands','andaman & nicobar':'andaman and nicobar islands','dadra and nagar haveli':'dadra and nagar haveli and daman and diu','nct of delhi':'delhi','n.c.t. of delhi':'delhi'});
  aliases['the dadra and nagar haveli and daman and diu']='dadra and nagar haveli and daman and diu';
  const canonical=value=>{const text=String(value||'').trim().replace(/\s+/g,' ').toLowerCase();return aliases[text]||text;};
  let reference;
  const ready=fetch('/static/pin-districts.json').then(async response=>{if(!response.ok)throw Error('PIN district reference could not be loaded.');reference=await response.json();if(reference.schema_version!==1)throw Error('Invalid PIN district reference.');});
  const derive=row=>{if(!reference)throw Error('PIN district reference is not ready.');const pin=String(row.postal_code||'').trim();if(!/^[1-9][0-9]{5}$/.test(pin))return null;return reference.states[canonical(row.state)]?.[pin]||null;};
  const api={derive,canonical,ready};
  if(typeof window!=='undefined')window.AtlasLocality=api;
  else self.AtlasLocality=api;
})();
