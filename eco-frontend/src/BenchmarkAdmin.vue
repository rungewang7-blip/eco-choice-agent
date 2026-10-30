<script setup lang="ts">
import {onUnmounted, reactive, ref} from 'vue'
type Source = {id:string;category:string;url:string|null;format:string;enabled:boolean}
type Report = {run_id:string; counts:Record<string,number>; sources:{source_id:string;status:string;error?:string}[]; records:{record_id:string;indicator:string;status:string;reasons:string[]}[]}
const token=ref(''), connected=ref(false), busy=ref(false), error=ref(''), notice=ref('')
const success=ref('')
let toastTimer: ReturnType<typeof setTimeout> | undefined
function dismissSuccess(){success.value='';clearTimeout(toastTimer)}
function showSuccess(message:string){dismissSuccess();success.value=message;toastTimer=setTimeout(dismissSuccess,6000)}
onUnmounted(dismissSuccess)
const sources=ref<Source[]>([]), report=ref<Report|null>(null), editing=ref(false)
const empty=():Source=>({id:'',category:'transport',url:'',format:'html',enabled:false})
const form=reactive<Source>(empty())
const base=(import.meta.env.VITE_API_BASE_URL||'')+'/admin/benchmark'
async function request(path:string,method='GET',body?:Source) {
 const response=await fetch(base+path,{method,credentials:'omit',headers:{Authorization:'Bearer '+token.value,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined})
 if(!response.ok) {
  if(response.status===401) connected.value=false
  const detail=await response.json().catch(()=>({detail:'Unable to read the server response'}))
  throw new Error(`${response.status}: ${typeof detail.detail==='string'?detail.detail:JSON.stringify(detail.detail)}`)
 }
 return response.status===204?null:response.json()
}
async function action(fn:()=>Promise<void>) {
 if(busy.value)return
 dismissSuccess()
 busy.value=true;error.value='';notice.value=''
 try {await fn()} catch(e) {error.value=e instanceof Error?e.message:'Operation failed'} finally {busy.value=false}
}
async function load(){sources.value=(await request('/sources')).sources}
function reset(){Object.assign(form,empty());editing.value=false}
function edit(source:Source){Object.assign(form,{id:source.id,category:source.category||'transport',url:source.url,format:source.format,enabled:source.enabled});editing.value=true}
function login(){void action(async()=>{await load();connected.value=true;notice.value='Connected. You can now manage sources and view reports.'})}
function logout(){dismissSuccess();error.value='';notice.value='';token.value='';connected.value=false;sources.value=[];report.value=null;reset()}
function save(){void action(async()=>{
 const wasEditing=editing.value
 const submitted={...form,url:form.url?.trim()||null}
 await request(wasEditing?'/sources/'+encodeURIComponent(submitted.id):'/sources',wasEditing?'PUT':'POST',submitted)
 showSuccess(wasEditing?`Source "${submitted.id}" updated successfully.`:`Source "${submitted.id}" saved successfully.`)
 reset()
 try {await load()} catch(e) {
  error.value=`Source "${submitted.id}" was saved, but the source list could not be refreshed. Reconnect to reload it. ${e instanceof Error?e.message:'Refresh failed'}`
 }
})}
function remove(source:Source){if(window.confirm(`Delete source ${source.id}?`)) void action(async()=>{await request('/sources/'+encodeURIComponent(source.id),'DELETE');await load();if(form.id===source.id)reset();notice.value='Source deleted.'})}
function collect(){void action(async()=>{report.value=await request('/collect','POST');notice.value='Collection finished. Review the source and record results.'})}
function latest(){void action(async()=>{report.value=await request('/report')})}
</script>

<template>
 <main class="admin">
  <aside v-if="success" class="success-toast" role="status" aria-live="polite" aria-atomic="true">
   <div><strong>Source saved</strong><p>{{success}}</p></div>
   <button type="button" aria-label="Dismiss success notification" @click="dismissSuccess">Close</button>
  </aside>
  <a href="/">Back to EcoChoice</a>
  <h1>Benchmark Source Manager</h1>
  <p>Data source management · Administrators only</p>
  <p>Enter a Source URL below. Each category can have multiple sources with unique IDs.</p>
  <form v-if="!connected" @submit.prevent="login">
   <label>Administrator token <input v-model="token" type="password" autocomplete="off" required minlength="32"></label>
   <button :disabled="busy">Connect</button>
  </form>
  <p role="alert" v-if="error">{{error}}</p><p role="status" v-if="notice">{{notice}}</p>
  <p v-if="busy" role="status">Processing. Collection may take several minutes. Please do not submit again.</p>
  <template v-if="connected">
   <button @click="logout" :disabled="busy">Sign out and clear token</button>
   <h2>{{editing?'Edit source':'Add source'}}</h2>
   <form @submit.prevent="save">
    <fieldset :disabled="busy">
     <label>Category <select v-model="form.category"><option value="transport">Transport</option><option value="diet">Diet</option><option value="home_energy">Home Energy</option><option value="consumer_items">Consumer Items</option></select></label>
     <label>Source ID <input v-model="form.id" required maxlength="80" pattern="[A-Za-z0-9_-]+" :disabled="editing"></label>
     <label>Source URL <input v-model="form.url" type="url" maxlength="2048" placeholder="https://www.cso.ie/…" :required="form.enabled"></label>
     <label>Format <select v-model="form.format"><option value="html">HTML</option><option value="csv">CSV</option><option value="json">JSON</option></select></label>
     <label><input v-model="form.enabled" type="checkbox">Enable source</label>
     <button type="submit">Save source</button> <button type="button" @click="reset">Clear / cancel editing</button>
    </fieldset>
   </form>
   <p>Only HTTPS URLs on the server allowlist are accepted. New sources are disabled by default. Verify extraction settings in sources.json before enabling them. Editing here preserves advanced settings.</p>
   <h2>Sources</h2>
   <div class="table-wrap"><table><thead><tr><th>ID / Category</th><th>URL / Format</th><th>Status</th><th>Actions</th></tr></thead><tbody>
    <tr v-for="source in sources" :key="source.id"><td>{{source.id}}<br>{{source.category||'Category not configured'}}</td><td>{{source.url||'URL not configured'}}<br>{{source.format}}</td><td>{{source.enabled?'Enabled':'Disabled'}}</td><td><button @click="edit(source)" :disabled="busy">Edit / disable</button> <button @click="remove(source)" :disabled="busy">Delete</button></td></tr>
   </tbody></table></div>
   <p v-if="!sources.length">No sources yet. Add a source to get started.</p>
   <button @click="collect" :disabled="busy">Run Collection</button> <button @click="latest" :disabled="busy">View latest report</button>
   <h2>Data Quality Report</h2>
   <p>PASS means the candidate checks passed. Human approval is still required. This action does not publish or change the official benchmark.</p>
   <template v-if="report">
    <p>Run: {{report.run_id}}</p>
    <p><strong v-for="status in ['PASS','REVIEW','REJECT']" :key="status">{{status}}: {{report.counts[status]||0}}　</strong></p>
    <h3>Source collection results</h3><ul><li v-for="source in report.sources" :key="source.source_id">{{source.source_id}} — {{source.status}} {{source.error}}</li></ul>
    <h3>Record quality results</h3><p v-if="!report.records.length">No candidate records. Check disabled sources, collection failures and field mappings. Zero records do not mean validation passed.</p>
    <ul><li v-for="row in report.records" :key="row.record_id"><strong>{{row.status}}</strong> · {{row.indicator||'Unknown indicator'}} — {{row.reasons.join('; ')||'Defined checks passed; awaiting human review'}}</li></ul>
   </template>
  </template>
 </main>
</template>

<style scoped>
.success-toast{position:fixed;top:1rem;right:1rem;z-index:1000;display:flex;gap:1rem;align-items:flex-start;max-width:calc(100vw - 2rem);box-sizing:border-box;width:420px;padding:1rem 1.25rem;background:#e8f7ee;color:#14532d;border:2px solid #27834e;border-radius:10px;box-shadow:0 6px 24px #173c3526;overflow-wrap:anywhere}.success-toast p{margin:.4rem 0 0}.success-toast button{flex-shrink:0;background:white;color:#14532d;border:1px solid #27834e;border-radius:5px}.admin [role=alert]{padding:1rem;background:#fff0f0;border:1px solid #a31b1b;border-radius:6px}

.admin{max-width:1100px;margin:2rem auto;padding:1.5rem;background:#fff;color:#173c35}.admin form{margin:1rem 0}.admin fieldset{border:1px solid #b9cfc6;padding:1rem}.admin label{display:block;margin:.8rem 0}.admin input:not([type=checkbox]),.admin select{display:block;width:100%;max-width:700px;padding:.65rem;border:1px solid #758b82;border-radius:5px}.admin button{padding:.6rem 1rem;margin:.3rem 0;cursor:pointer}.admin button:disabled{opacity:.5;cursor:wait}.admin table{width:100%;border-collapse:collapse}.admin td,.admin th{text-align:left;padding:.8rem;border-bottom:1px solid #ccd8d2;overflow-wrap:anywhere}.table-wrap{overflow:auto}.admin [role=alert]{color:#a31b1b}.admin li{margin:.7rem 0}
</style>
