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

const base={total:4,described:2,capital_placements:[{rank:1,priority_index:0,base_before:1},{rank:2,priority_index:1,base_before:1}]};
const overlay={base_total:4,base_described:2,added:1,sources:[{kind:'flag',cin:'flag'},{kind:'base',index:0},{kind:'base',index:1}],capital_placements:[{rank:1,priority_index:0,base_before:1},{rank:2,priority_index:1,base_before:1},{rank:3,priority_index:2,base_before:1}]};
const expanded=index.expand(base,overlay),capital=[3,0,1,2,4],reviewed=[0,3];
assert.equal(expanded.total,5);assert.equal(expanded.described,3);assert.equal(index.fromBase(0,expanded),1);assert.equal(index.fromBase(2,expanded),3);assert.equal(index.fromBase(-1,expanded),-1);assert.equal(index.toBase(0,expanded).kind,'flag');assert.equal(index.toBase(4,expanded).index,3);
for(const order of ['priority','capital'])for(const reason of ['all','audit_flags','multiple_candidates'])for(const mode of ['pending','checked','all']){
 const ordered=order==='priority'?[0,1,2,3,4]:capital,expected=ordered.filter(i=>(reason==='all'||(i===0)===(reason==='audit_flags'))&&(mode==='all'||reviewed.includes(i)===(mode==='checked')));
 for(let page=1;page<=4;page++){const result=index.positions(expanded,reviewed,mode,order,page,2,reason);assert.deepEqual([...result.indices],expected.slice((result.page-1)*2,result.page*2));assert.equal(result.total,expected.length);assert.equal(result.summary.audit_flagged,1);assert.equal(result.summary.total,5);assert.equal(result.summary.checked,2);}
}
assert.throws(()=>index.expand({...base,total:99},overlay),/overlay/);
console.log('Sparse audit overlays preserve old pages, capital ordering, reason filters and review progress.');
