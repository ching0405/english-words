const {test}=require('node:test'),assert=require('node:assert/strict');
const P=require('../js/phrases'),Progress=require('../js/progress'),phrases=require('../data/phrases.json');
test('every phrase once per round, distinct namespaced IDs, at most four words',()=>{
 assert.equal(new Set(phrases.map(p=>p.id)).size,phrases.length);
 const round=P.round(phrases,()=>.5);assert.equal(round.length,phrases.length);assert.equal(new Set(round.map(p=>p.id)).size,phrases.length);
 phrases.forEach(p=>{assert.match(p.id,/^phrase_/);assert.ok(P.tokens(p).length<=4);P.tokens(p).forEach((_,i)=>{assert.ok(P.accepts(p,i,i));assert.ok(!P.accepts(p,i,(i+1)%4));});assert.ok(!P.accepts(p,4,4));});
});
test('v3 saves preserve words, phrases, jar and tomorrow review independently',()=>{
 let raw=null,now=new Date(2026,9,22,19).getTime();const storage={getItem:()=>raw,setItem:(_,v)=>raw=v};
 let progress=Progress.create(storage,()=>now);progress.seen('goat');progress.answer(phrases[0].id,false);progress.answer(phrases[1].id,true);progress.addJarStars(3);
 progress=Progress.create(storage,()=>now);assert.equal(progress.get('goat').seen,1);assert.equal(progress.get(phrases[0].id).wrong,1);assert.equal(progress.jar().stars,3);assert.equal(progress.due(phrases).length,0);
 now=Progress.dayAfter(now,1)+1;assert.equal(progress.reviewSet(phrases,4).list[0].id,phrases[0].id);assert.equal(progress.due(phrases).length,2);
});

test('scenario choices include answer once, at most four unique options even with small lists',()=>{
 for(let n=1;n<=phrases.length;n++){
   const all=phrases.slice(0,n);
   all.forEach(answer=>{const options=P.choices(answer,all,Math.random);assert.equal(options.length,Math.min(n,4));assert.equal(new Set(options.map(p=>p.id)).size,options.length);assert.equal(options.filter(p=>p.id===answer.id).length,1);});
 }
 assert.equal(P.accepts(phrases[0],-1,-1),false);assert.equal(P.accepts(phrases[0],.5,.5),false);
});

test('order game uses only the multi-word phrases (2–4 words), without adding any',()=>{
 assert.deepEqual(P.orderable(phrases).map(p=>p.id),phrases.filter(p=>P.tokens(p).length>=2).map(p=>p.id));
 assert.ok(P.orderable(phrases).length>0);
});

test('phrase review: due first, then missed and not relearned, at most n',()=>{
 const [a,b,c,d,e]=phrases;
 const records={[b.id]:{wrong:1,box:0},[c.id]:{wrong:2,box:2},[e.id]:{wrong:1,box:0}};
 const set={due:[d],list:[d,a,b,c,e]};
 assert.deepEqual(P.reviewList(set,id=>records[id]||null,4).map(p=>p.id),[d.id,b.id,e.id,a.id]);
});
test('F5: two phrases sharing one picture are never choices together',()=>{
  const twin={id:'my_phrase_hi',english:'Hi.',category:'custom',image:phrases[0].image};
  for(let s=0;s<200;s++){const c=P.choices(twin,phrases.concat([twin]),Math.random);assert.equal(new Set(c.map(p=>p.image)).size,c.length);}
});
