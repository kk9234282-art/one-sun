import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const context={self:{}};vm.createContext(context);vm.runInContext(await readFile(new URL('../intelligence/static/queue-index.js',import.meta.url),'utf8'),context);const index=context.self.AtlasQueueIndex;
let seed=17;const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
for(let sample=0;sample<70;sample++){
 const total=Math.floor(rand()*40),capitalOrder=Array.from({length:total},(_,i)=>({id:i,hasSource:rand()<.3})),priority=[...capitalOrder].sort((a,b)=>Number(b.hasSource)-Number(a.hasSource)||a.id-b.id),meta={total,described:priority.filter(r=>r.hasSource).length,capital_placements:capitalOrder.map((r,rank)=>({r,rank})).filter(({r})=>r.hasSource).map(({r,rank},i)=>({rank,priority_index:priority.indexOf(r),base_before:rank-i}))},checked=priority.map((_,i)=>i).filter(()=>rand()<.4);
 for(const order of ['priority','capital']){
  const rows=order==='priority'?priority:capitalOrder;
  for(let rank=0;rank<total;rank++){const p=index.rankToPriority(rank,meta,order);assert.equal(priority[p].id,rows[rank].id);assert.equal(index.priorityToRank(p,meta,order),rank);}
  for(const mode of ['pending','checked','all']){
   const selected=rows.filter(row=>mode==='all'||checked.includes(priority.indexOf(row))===(mode==='checked'));
   for(let page=1;page<=Math.ceil(selected.length/7)+1;page++){
    const result=index.positions(meta,[...checked,...checked,-1,total+1],mode,order,page,7),expected=selected.slice((result.page-1)*7,result.page*7).map(row=>priority.indexOf(row));assert.deepEqual([...result.indices],expected);assert.equal(result.total,selected.length);assert.equal(result.summary.checked,checked.length);assert.equal(result.summary.pending,total-checked.length);
   }
  }
 }
}
assert.equal(index.bucket('U15511MH2010PTC000001',128),77);
console.log('Queue sparse ordering, pending/checked pagination, exact progress and page clamping passed.');
