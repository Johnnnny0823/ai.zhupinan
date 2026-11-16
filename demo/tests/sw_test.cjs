const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function worker(){
 const handlers={},entries=new Map(),requests=[];let net=true;
 const cache={put:async(k,v)=>entries.set(k,v),match:async k=>entries.get(k)};
 const context={URL,Response,Error,self:{location:{origin:'https://demo.example'},addEventListener:(e,f)=>handlers[e]=f,skipWaiting:async()=>{},clients:{claim:async()=>{}}},caches:{open:async()=>cache,keys:async()=>['old-unrelated','zpa-public-old'],delete:async k=>k.startsWith('zpa-public-')},fetch:async(req,opts)=>{requests.push([req,opts]);if(!net)throw Error('offline');return new Response(typeof req==='string'?req:req.url)}};
 vm.runInNewContext(fs.readFileSync('demo/web/sw.js','utf8'),context);
 return {handlers,entries,requests,offline:()=>net=false};
}
test('precache is public and fetched without cookies',async()=>{const w=worker();let pending;w.handlers.install({waitUntil:p=>pending=p});await pending;assert(w.entries.has('/offline.html'));for(const [path,opts] of w.requests){assert.equal(opts.credentials,'omit');assert(!path.startsWith('/api/'));assert(!path.includes('samples'));}});
for(const path of ['/api/cases','/api/qa','/api/tasks/1/proof','/line/webhook','/samples/test.png','/unknown.txt'])test('never intercepts '+path,()=>{const w=worker();let intercepted=false;w.handlers.fetch({request:{url:'https://demo.example'+path,method:'GET',mode:'cors'},respondWith:()=>intercepted=true});assert.equal(intercepted,false);assert.equal(w.entries.size,0);});
test('offline navigation uses public page, not case shell',async()=>{const w=worker();let pending;w.handlers.install({waitUntil:p=>pending=p});await pending;w.offline();w.handlers.fetch({request:{url:'https://demo.example/',method:'GET',mode:'navigate'},respondWith:p=>pending=p});assert.equal(await(await pending).text(),'/offline.html');});
test('offline local demo remains explicitly separate',async()=>{const w=worker();let pending;w.handlers.install({waitUntil:p=>pending=p});await pending;w.offline();w.handlers.fetch({request:{url:'https://demo.example/local-demo.html',method:'GET',mode:'navigate'},respondWith:p=>pending=p});assert.equal(await(await pending).text(),'/local-demo.html');});
