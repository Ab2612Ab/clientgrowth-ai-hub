(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const toast = (message, ok=true) => {
    let el = $('#cg-toast');
    if (!el) { el=document.createElement('div'); el.id='cg-toast'; document.body.appendChild(el); }
    el.textContent=message; el.dataset.ok=ok; el.classList.add('show');
    clearTimeout(window.__cgToast); window.__cgToast=setTimeout(()=>el.classList.remove('show'),2800);
  };
  const json = async (url, options={}) => {
    const r=await fetch(url,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
    const data=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(data.detail||'Request failed');
    return data;
  };
  window.CG={toast,json};

  $$('.cg-api-form').forEach(form=>form.addEventListener('submit',async e=>{
    e.preventDefault();
    const button=$('button[type=submit]',form); const old=button?.textContent;
    if(button){button.disabled=true;button.textContent='Working…';}
    try{
      const payload=Object.fromEntries(new FormData(form).entries());
      const data=await json(form.dataset.endpoint,{method:form.dataset.method||'POST',body:JSON.stringify(payload)});
      const target=form.dataset.result;
      if(target && data.data) { const box=$(target); if(box) box.textContent=data.data.message||JSON.stringify(data.data,null,2); }
      toast(form.dataset.success||'Action completed.');
    }catch(err){toast(err.message,false)}finally{if(button){button.disabled=false;button.textContent=old;}}
  }));

  $$('.stage-action').forEach(button=>button.addEventListener('click',async()=>{
    if (button.closest('form')) return; // native server-side form handles this action
    try{
      const data=await json(`/api/leads/${button.dataset.id}/stage`,{method:'PATCH',body:JSON.stringify({stage:button.dataset.stage})});
      button.closest('.deal')?.remove(); toast(`${data.data.name} moved to ${data.data.stage}.`); setTimeout(()=>location.reload(),500);
    }catch(err){toast(err.message,false)}
  }));

  $$('.automation-action').forEach(button=>button.addEventListener('click',async()=>{
    if (button.closest('form')) return; // native server-side form handles this action
    try{const data=await json(`/api/automations/${button.dataset.automation}`,{method:'POST',body:'{}'});toast(data.message)}catch(err){toast(err.message,false)}
  }));

  $$('.copy-draft').forEach(button=>button.addEventListener('click',async()=>{
    const text=$(button.dataset.target)?.textContent||'';
    try{await navigator.clipboard.writeText(text);toast('Draft copied to clipboard.')}catch{toast('Copy failed.',false)}
  }));
})();
