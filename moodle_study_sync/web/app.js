const $=id=>document.getElementById(id);
const TOKEN=location.hash.slice(1)||sessionStorage.getItem('study-session')||'';
if(TOKEN){sessionStorage.setItem('study-session',TOKEN);history.replaceState(null,'',location.pathname);}
let state=null,catalog=null,selectedSemester='',currentPage='library',pendingAdd=false,wasJobRunning=false,lastJobMessage='';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=value=>String(value).toLocaleLowerCase('pt-BR').replace(/(^|\s)(\p{L})/gu,(_,space,letter)=>space+letter.toLocaleUpperCase('pt-BR')).replace(/\b(De|Da|Do|Das|Dos|E|Para)\b/g,s=>s.toLowerCase());
const key=value=>value.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().replace(/[^a-z0-9]/g,'');
async function api(path,payload){const response=await fetch(path,{method:payload===undefined?'GET':'POST',headers:{'X-Study-Token':TOKEN,...(payload===undefined?{}:{'Content-Type':'application/json'})},...(payload===undefined?{}:{body:JSON.stringify(payload)})});let body;try{body=await response.json();}catch{throw Error('Não foi possível conversar com o app. Abra novamente pelo atalho.');}if(!response.ok)throw Error(body.message||'Não foi possível concluir.');return body;}
let toastTimer;
function toast(message,error=false){$('toast').textContent=message;$('toast').className='toast'+(error?' error':'');$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,6500);}
function page(name){currentPage=name;$('library-page').hidden=name!=='library';$('connections-page').hidden=name!=='connections';$('nav-library').classList.toggle('active',name==='library'&&!selectedSemester);$('nav-connections').classList.toggle('active',name==='connections');$('breadcrumb').textContent=name==='connections'?'Contas conectadas':'Biblioteca';render();}
function render(){if(!state)return;const groups=state.groups,busy=state.busy||state.job.running;
 $('schedule').textContent=state.schedule;
 $('stat-subjects').textContent=groups.length;
 $('stat-materials').textContent=groups.reduce((sum,g)=>sum+g.resources,0);
 $('stat-status').textContent=busy?'Organizando…':state.last_sync.status==='attention_required'?'Precisa de atenção':state.last_sync.status==='ok'?'Tudo atualizado':'Vamos começar';
 const date=state.last_sync.finished_at_utc;
 $('stat-last').textContent=date?'Última atualização: '+new Intl.DateTimeFormat('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'}).format(new Date(date)):'As matérias ativas seguem a rotina diária';
 const semesters=[...new Set(groups.map(g=>g.semester))];
 $('semester-nav').innerHTML=semesters.map(s=>`<button class="nav semester ${currentPage==='library'&&selectedSemester===s?'active':''}" data-semester="${esc(s)}">${esc(pretty(s))}</button>`).join('');
 $('semester-nav').querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{selectedSemester=button.dataset.semester;page('library');}));
 $('nav-library').classList.toggle('active',currentPage==='library'&&!selectedSemester);
 $('section-title').textContent=selectedSemester?pretty(selectedSemester):'Todas as matérias';
 const shown=groups.filter(g=>!selectedSemester||g.semester===selectedSemester);
 $('section-caption').textContent=shown.length?`${shown.length} matérias · cada uma com seu notebook.`:'Um novo espaço para o que você vai aprender.';
 $('empty').hidden=shown.length>0;
 const icons=['↗','▤','⌘','⌁','ϟ','▥'];
 const expanded=new Set([...$('cards').querySelectorAll('details[open]')].map(d=>d.dataset.issue));
 $('cards').innerHTML=shown.map((g,i)=>{const active=busy&&state.progress.course_id&&g.rooms.some(r=>r.id===state.progress.course_id);const cls=!g.enabled?'paused':active?'waiting':g.status==='attention_required'?'attention':g.status==='ok'?'':'waiting';const status=!g.enabled?'Pausada':active?'Atualizando':g.status==='attention_required'?'Revisar':g.status==='ok'?'Atualizada':'Aguardando';return `<article class="subject-card"><div class="card-top"><span class="subject-icon tone-${i%6}">${icons[i%6]}</span><span class="badge ${cls}">${status}</span></div><h3>${esc(pretty(g.name))}</h3><span class="card-semester">${esc(pretty(g.semester))}</span><div class="card-meta"><span>▤ ${g.resources} materiais</span>${g.rooms.map(r=>`<span class="room-chip">${esc(r.name)}</span>`).join('')}</div>${g.local_only?`<p class="material-note">${g.local_only} arquivo(s) disponíveis só na pasta local — formato de laboratório.</p>`:''}${g.details.length?`<details class="issue-list" data-issue="${esc(g.key)}" ${expanded.has(g.key)?'open':''}><summary>Ver ${g.details.length} pendência(s)</summary>${g.details.map(d=>`<p><b>${esc(d.title)}</b><br>${d.action==='processing_failed_review'?'O Google não conseguiu processar este arquivo. O original continua na pasta de materiais.':d.action==='retry'?'Tente Atualizar agora. Se o acesso venceu, reconecte a conta em Contas conectadas.':'Este material precisa de conferência. Atualize novamente; se persistir, consulte a pasta de materiais.'}</p>`).join('')}</details>`:''}<div class="card-bottom"><a class="notebook-link" href="https://notebook.google.com/notebook/${encodeURIComponent(g.notebook_id)}" target="_blank" rel="noopener">Abrir notebook <span>↗</span></a><button class="pause-button" data-toggle="${esc(g.key)}" ${busy?'disabled':''}>${g.enabled?'Pausar':'Reativar'}</button></div></article>`;}).join('');
 $('cards').querySelectorAll('[data-toggle]').forEach(button=>button.addEventListener('click',()=>{const group=groups.find(g=>g.key===button.dataset.toggle);request('/api/toggle',{notebook_id:group.notebook_id,semester:group.semester,enabled:!group.enabled});}));
 $('progress').hidden=!busy;
 $('progress-title').textContent=state.progress.course?pretty(state.progress.course):state.job.running?({refresh:'Conferindo suas contas',add:'Adicionando matéria',google:'Conectando Google',moodle:'Conectando Moodle'}[state.job.action]||'Atualizando sua biblioteca'):'Atualizando sua biblioteca';
 $('progress-detail').textContent=state.progress.message||'Conferindo acesso e materiais disponíveis…';
 ['sync-button','moodle-connect','google-connect','refresh-catalog','save-course'].forEach(id=>$(id).disabled=busy);
 $('sync-button').textContent=busy?'↻ Atualizando…':'↻ Atualizar agora';
 $('save-course').textContent=pendingAdd?'Adicionando…':'Adicionar à rotina ↗';
 $('moodle-status').textContent=state.connections.moodle?'✓ Acesso salvo neste computador':'Conecte sua conta institucional';
 $('google-status').textContent=state.connections.google?'✓ Acesso salvo neste computador':'Conecte sua conta Google';
 let cp=$('connection-progress');if(!cp){cp=document.createElement('p');cp.id='connection-progress';cp.className='form-note';$('connections-page').insertBefore(cp,$('connections-page').querySelector('.connection-grid'));}cp.hidden=!(state.job.running&&['moodle','google'].includes(state.job.action));cp.textContent='Uma janela do navegador será aberta. Conclua o acesso nela; a confirmação aparece aqui automaticamente.';
 if(pendingAdd&&!state.job.running&&state.job.action==='add'){pendingAdd=false;if(state.job.error){$('form-error').textContent=state.job.message;$('form-error').hidden=false;}else{$('add-dialog').close();catalog=null;}}
 if(wasJobRunning&&!state.job.running&&state.job.message&&state.job.message!==lastJobMessage){toast(state.job.message,state.job.error);lastJobMessage=state.job.message;}
 wasJobRunning=state.job.running;
}
async function poll(){try{state=await api('/api/state');render();}catch(error){$('stat-status').textContent='App desconectado';$('stat-last').textContent='Abra novamente pelo atalho Meus Estudos';if(!state)toast(error.message,true);}finally{setTimeout(poll,2200);}}
async function request(path,payload={}){try{await api(path,payload);await fetchState();return true;}catch(error){toast(error.message,true);return false;}}
async function fetchState(){state=await api('/api/state');render();}
async function loadCatalog(){catalog=await api('/api/catalog');const assigned=new Set(state.groups.flatMap(g=>g.rooms.map(r=>r.id)));const available=catalog.moodle.filter(row=>!assigned.has(String(row.id)));$('course-select').innerHTML='<option value="">Selecione uma sala do Moodle</option>'+available.map(row=>`<option value="${esc(row.id)}">${esc(pretty(row.name))} · ${esc(row.room)}${row.period?' · '+esc(row.period):''}</option>`).join('');if(!available.length)$('course-select').innerHTML='<option value="">Todas as salas disponíveis já foram adicionadas</option>';$('notebook-select').innerHTML='<option value="">Criar notebook com o nome da matéria</option>'+catalog.notebooks.map(n=>`<option value="${esc(n.id)}">${esc(n.title)}</option>`).join('');}
async function openAdd(){if(!state)return;$('add-form').reset();$('form-error').hidden=true;$('new-title-label').hidden=false;$('notebook-title').hidden=false;$('semester-input').value=selectedSemester||state.groups[0]?.semester||'';$('semesters-list').innerHTML=[...new Set(state.groups.map(g=>g.semester))].map(s=>`<option value="${esc(s)}"></option>`).join('');$('add-dialog').showModal();try{await loadCatalog();}catch(error){$('form-error').textContent=error.message;$('form-error').hidden=false;}}
$('nav-library').addEventListener('click',()=>{selectedSemester='';page('library');});$('nav-connections').addEventListener('click',()=>page('connections'));
['add-button','empty-add'].forEach(id=>$(id).addEventListener('click',openAdd));
['close-dialog','cancel-dialog'].forEach(id=>$(id).addEventListener('click',()=>{if(!pendingAdd)$('add-dialog').close();}));
$('course-select').addEventListener('change',()=>{const course=catalog?.moodle.find(row=>String(row.id)===$('course-select').value);if(!course)return;$('subject-name').value=course.name;$('notebook-title').value=course.name;const existing=state.groups.find(g=>key(g.name)===key(course.name));$('notebook-select').value=existing?.notebook_id||'';showNotebookTitle();});
function showNotebookTitle(){const create=!$('notebook-select').value;$('new-title-label').hidden=!create;$('notebook-title').hidden=!create;}
$('notebook-select').addEventListener('change',showNotebookTitle);
$('subject-name').addEventListener('input',()=>{if(!$('notebook-select').value)$('notebook-title').value=$('subject-name').value;});
$('add-form').addEventListener('submit',async event=>{event.preventDefault();$('form-error').hidden=true;try{await api('/api/add',{course_id:$('course-select').value,name:$('subject-name').value,semester:$('semester-input').value,notebook_id:$('notebook-select').value||null,notebook_title:$('notebook-title').value});pendingAdd=true;await fetchState();}catch(error){$('form-error').textContent=error.message;$('form-error').hidden=false;}});
$('refresh-catalog').addEventListener('click',async()=>{if(await request('/api/refresh')){const refresh=setInterval(async()=>{const s=await api('/api/state');if(!s.job.running){clearInterval(refresh);await loadCatalog();}},1200);}});
$('sync-button').addEventListener('click',()=>request('/api/sync'));
$('folder-button').addEventListener('click',()=>request('/api/open-library'));
$('google-connect').addEventListener('click',()=>request('/api/connect-google'));
$('moodle-connect').addEventListener('click',()=>request('/api/connect-moodle'));
poll();
