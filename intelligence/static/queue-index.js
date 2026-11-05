/* Sparse priority/capital ordering, audit overlays and exact review pagination. */
'use strict';
(() => {
 const upper=(values,value)=>{let lo=0,hi=values.length;while(lo<hi){const mid=(lo+hi)>>1;if(values[mid]<=value)lo=mid+1;else hi=mid;}return lo;};
 function expand(meta,overlay){if(!overlay)return meta;if(overlay.base_total!==meta.total||overlay.base_described!==meta.described||!Number.isInteger(overlay.added)||overlay.added<0||overlay.sources.length!==meta.described+overlay.added||overlay.capital_placements.length!==overlay.sources.length)throw Error('Audit queue overlay does not match the base queue.');return {...meta,total:meta.total+overlay.added,described:meta.described+overlay.added,capital_placements:overlay.capital_placements,overlay};}
 function toBase(index,meta){if(!meta.overlay)return {kind:'base',index};return index<meta.described?meta.overlay.sources[index]:{kind:'base',index:index-meta.overlay.added};}
 function fromBase(index,meta){if(!meta.overlay||index<0)return index;if(index>=meta.overlay.base_described)return index+meta.overlay.added;return meta.overlay.sources.findIndex(item=>item.kind==='base'&&item.index===index);}
 function flagIndices(meta){return meta.overlay?meta.overlay.sources.map((item,index)=>item.kind==='flag'?index:-1).filter(index=>index>=0):[];}
 function rankToPriority(rank,meta,order){if(order!=='capital')return rank;const positions=meta.capital_placements,at=upper(positions.map(p=>p.rank),rank)-1;if(at>=0&&positions[at].rank===rank)return positions[at].priority_index;return meta.described+rank-(at+1);}
 function priorityToRank(index,meta,order){if(order!=='capital')return index;if(index<meta.described)return meta.capital_placements.find(p=>p.priority_index===index).rank;const base=index-meta.described;return base+upper(meta.capital_placements.map(p=>p.base_before),base);}
 function positions(meta,checkedPriority,mode,order,page,size,reason='all'){
  const checked=[...new Set(checkedPriority)].filter(index=>Number.isInteger(index)&&index>=0&&index<meta.total).map(index=>priorityToRank(index,meta,order)).sort((a,b)=>a-b),flags=flagIndices(meta).map(index=>priorityToRank(index,meta,order)).sort((a,b)=>a-b),checkedSet=new Set(checked),summary={total:meta.total,checked:checked.length,pending:meta.total-checked.length,source_described:meta.described,audit_flagged:flags.length};
  if(reason==='audit_flags'){const chosen=flags.filter(rank=>mode==='all'||checkedSet.has(rank)===(mode==='checked'));page=Math.min(Math.max(1,page),Math.max(1,Math.ceil(chosen.length/size)));return {indices:chosen.slice((page-1)*size,page*size).map(rank=>rankToPriority(rank,meta,order)),total:chosen.length,page,per_page:size,summary};}
  const excluded=new Set(reason==='multiple_candidates'?flags:[]),eligibleChecked=checked.filter(rank=>!excluded.has(rank)),eligibleTotal=meta.total-excluded.size,total=mode==='checked'?eligibleChecked.length:mode==='pending'?eligibleTotal-eligibleChecked.length:eligibleTotal;page=Math.min(Math.max(1,page),Math.max(1,Math.ceil(total/size)));const offset=(page-1)*size,ranks=[];
  if(mode==='checked')ranks.push(...eligibleChecked.slice(offset,offset+size));
  else{const blocked=[...new Set([...excluded,...(mode==='pending'?eligibleChecked:[])])].sort((a,b)=>a-b);let lo=0,hi=meta.total;while(lo<hi){const mid=(lo+hi)>>1;if(mid+1-upper(blocked,mid)>offset)hi=mid;else lo=mid+1;}const skip=new Set(blocked);for(let rank=lo;rank<meta.total&&ranks.length<size;rank++)if(!skip.has(rank))ranks.push(rank);}
  return {indices:ranks.map(rank=>rankToPriority(rank,meta,order)),total,page,per_page:size,summary};
 }
 function bucket(cin,count){let hash=2166136261;for(const char of cin)hash=Math.imul(hash^char.charCodeAt(0),16777619)>>>0;return hash%count;}
 self.AtlasQueueIndex={upper,expand,toBase,fromBase,flagIndices,rankToPriority,priorityToRank,positions,bucket};
})();
