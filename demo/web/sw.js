/* Public, versioned shell only. Nothing from API, LINE, documents or proof is cached. */
const VERSION='zpa-public-2026-11-15-v2';
const PUBLIC=['/','/index.html','/app.css','/app.js','/offline.html','/local-demo.html','/local-demo.js','/local-demo-data.json','/app.webmanifest','/icons/icon-192.png','/icons/icon-512.png'];
self.addEventListener('install',event=>event.waitUntil((async()=>{
  const cache=await caches.open(VERSION);
  for(const path of PUBLIC){
    const response=await fetch(path,{credentials:'omit',cache:'reload'});
    if(!response.ok)throw new Error('public shell unavailable');
    await cache.put(path,response);
  }
  await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  for(const key of await caches.keys())if(key.startsWith('zpa-public-')&&key!==VERSION)await caches.delete(key);
  await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
  const req=event.request,url=new URL(req.url);
  // Pass protected and unknown requests straight to the network without interception.
  if(url.origin!==self.location.origin || req.method!=='GET' || url.search || !PUBLIC.includes(url.pathname))return;
  if(req.mode==='navigate'){
    event.respondWith(fetch(req).catch(async()=>{
      const cache=await caches.open(VERSION);
      return await cache.match(url.pathname==='/local-demo.html'?'/local-demo.html':'/offline.html');
    }));return;
  }
  // Cache entries were created exclusively with credentials:omit, and never updated from credentialed responses.
  event.respondWith(fetch(req).catch(async()=>{
    const cache=await caches.open(VERSION);return await cache.match(url.pathname)||Response.error();
  }));
});
