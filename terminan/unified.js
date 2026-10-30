/* Six bounded lazy workspaces. Retained documents preserve chart/graph state. */
'use strict';
(()=>{
 const pages={'/':'terminal','/saved':'saved','/math':'math','/history-overlay':'history-overlay','/monitor':'monitor','/cache':'cache'};
 const frames=new Map(),host=document.getElementById('workspace-host');
 function show(path,push){
  if(!Object.hasOwn(pages,path))return;
  if(push&&location.pathname!==path)history.pushState(null,'',path);
  let frame=frames.get(path);
  if(!frame){frame=document.createElement('iframe');frame.src='/workspace/'+pages[path];frame.title=pages[path];frame.dataset.workspace=pages[path];frame.addEventListener('load',()=>{frame.contentDocument.addEventListener('click',e=>{const a=e.target.closest('a');if(!a||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href);if(u.origin===location.origin&&Object.hasOwn(pages,u.pathname)&&!u.search&&!u.hash){e.preventDefault();show(u.pathname,true);}});});frames.set(path,frame);host.append(frame);}
  for(const [key,item] of frames){if(key!==path&&!item.hidden){item.contentWindow?.r4?.pause();item.contentWindow?.saved?.pause();}item.hidden=key!==path;}
  for(const link of document.querySelectorAll('#workspaces a')){if(link.getAttribute('href')===path)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 }
 document.getElementById('workspaces').addEventListener('click',event=>{const a=event.target.closest('a');if(!a||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();show(a.getAttribute('href'),true);});
 addEventListener('popstate',()=>show(location.pathname,false));show(location.pathname,false);
 window.unified={count:()=>frames.size};
})();
