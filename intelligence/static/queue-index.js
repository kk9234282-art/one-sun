/* Sparse capital-order mapping and pending pagination; no full queue download. */
'use strict';
(() => {
 const upper=(values,value)=>{let lo=0,hi=values.length;while(lo<hi){const mid=(lo+hi)>>1;if(values[mid]<=value)lo=mid+1;else hi=mid;}return lo;};
 function rankToPriority(rank,meta,order){if(order!=='capital')return rank;const positions=meta.capital_placements,at=upper(positions.map(p=>p.rank),rank)-1;if(at>=0&&positions[at].rank===rank)return positions[at].priority_index;return meta.described+rank-(at+1);}
 function priorityToRank(index,meta,order){if(order!=='capital')return index;if(index<meta.described)return meta.capital_placements.find(p=>p.priority_index===index).rank;const base=index-meta.described;return base+upper(meta.capital_placements.map(p=>p.base_before),base);}
 function positions(meta,checkedPriority,mode,order,page,size){
  const checked=[...new Set(checkedPriority)].filter(index=>Number.isInteger(index)&&index>=0&&index<meta.total).map(index=>priorityToRank(index,meta,order)).sort((a,b)=>a-b),total=mode==='checked'?checked.length:mode==='pending'?meta.total-checked.length:meta.total,last=Math.max(1,Math.ceil(total/size));page=Math.min(Math.max(1,page),last);const offset=(page-1)*size,ranks=[];
  if(mode==='checked')ranks.push(...checked.slice(offset,offset+size));
  else{let start=offset;if(mode==='pending'){let lo=0,hi=meta.total;while(lo<hi){const mid=(lo+hi)>>1;if(mid+1-upper(checked,mid)>offset)hi=mid;else lo=mid+1;}start=lo;}const excluded=new Set(mode==='pending'?checked:[]);for(let rank=start;rank<meta.total&&ranks.length<size;rank++)if(!excluded.has(rank))ranks.push(rank);}
  return {indices:ranks.map(rank=>rankToPriority(rank,meta,order)),total,page,per_page:size,summary:{total:meta.total,checked:checked.length,pending:meta.total-checked.length,source_described:meta.described}};
 }
 function bucket(cin,count){let hash=2166136261;for(const char of cin)hash=Math.imul(hash^char.charCodeAt(0),16777619)>>>0;return hash%count;}
 self.AtlasQueueIndex={upper,rankToPriority,priorityToRank,positions,bucket};
})();
