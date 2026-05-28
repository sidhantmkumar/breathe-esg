content = open('templates/index.html', encoding='utf-8').read()

content = content.replace(
    "async function approve(id){try{await apiFetch(`/records/${id}/approve/`,{method:'POST',body:JSON.stringify({})});toast.success('Approved');load();}catch(e){toast.success('Done');load();}",
    "async function approve(id){fetch('/api/records/'+id+'/approve/',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},body:'{}'}).then(r=>r.json()).then(()=>{toast.success('Row approved');load();}).catch(()=>{load();});}"
)

content = content.replace(
    "async function reject(id){try{await apiFetch(`/records/${id}/reject/`,{method:'POST',body:JSON.stringify({})});toast.success('Rejected');load();}catch(e){toast.success('Done');load();}",
    "async function reject(id){fetch('/api/records/'+id+'/reject/',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},body:'{}'}).then(r=>r.json()).then(()=>{toast.success('Row rejected');load();}).catch(()=>{load();});}"
)

open('templates/index.html', 'w', encoding='utf-8').write(content)
print('Done')