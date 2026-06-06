const $ = (id)=>document.getElementById(id);
const KEY='lecturenote_action_key', SUBJECT='lecturenote_subject';
let currentSourceId=''; let currentSourceType='generated_note';
function key(){return $('key').value.trim()} function subject(){return $('subject').value.trim()}
function headers(json=true){const h={}; if(key()) h.Authorization='Bearer '+key(); if(json) h['Content-Type']='application/json'; return h}
function remember(){ if(key()) localStorage.setItem(KEY,key()); if(subject()) localStorage.setItem(SUBJECT,subject()); }
function restore(){ $('key').value=localStorage.getItem(KEY)||''; $('subject').value=localStorage.getItem(SUBJECT)||''; }
function status(t){ $('saveState').textContent=t; }
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(path,opt={}){remember(); const res=await fetch(path,opt); if(!res.ok) throw new Error(await res.text()); return await res.json();}
function render(md){
  md = String(md||'');
  const stash=[];
  md = md.replace(/```([\s\S]*?)```/g,(_,c)=>{stash.push('<pre><code>'+esc(c)+'</code></pre>'); return `\u0000${stash.length-1}\u0000`;});
  md = esc(md);
  md = md.replace(/^### (.*)$/gm,'<h3>$1</h3>').replace(/^## (.*)$/gm,'<h2>$1</h2>').replace(/^# (.*)$/gm,'<h1>$1</h1>');
  md = md.replace(/!\[([^\]]*)\]\(([^)]+)\)/g,'<img alt="$1" src="$2">');
  md = md.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>');
  md = md.replace(/&lt;mark&gt;([\s\S]*?)&lt;\/mark&gt;/g,'<mark>$1</mark>');
  md = md.replace(/^(?:- |\* )(.*)$/gm,'<li>$1</li>').replace(/(<li>[\s\S]*?<\/li>\n?)+/g,m=>'<ul>'+m+'</ul>');
  md = md.split(/\n{2,}/).map(block=>/^\s*<(h\d|ul|pre|img|blockquote|table)/.test(block)?block:'<p>'+block.replace(/\n/g,'<br>')+'</p>').join('\n');
  md = md.replace(/\u0000(\d+)\u0000/g,(_,i)=>stash[Number(i)]||'');
  $('preview').innerHTML=md;
  if(window.MathJax?.typesetPromise) MathJax.typesetPromise([$ ('preview')]).catch(()=>{});
}
function onEdit(){ render($('markdown').value); status('수정됨'); }
async function listNotes(){ try{ remember(); const params=new URLSearchParams(); if(subject()) params.set('subject',subject()); if($('sourceType').value) params.set('source_type',$('sourceType').value); const data=await api('/study/notes?'+params,{headers:headers(false)}); const list=data.notes||[]; $('list').innerHTML=list.length?'':'<div class="item"><span>자료 없음</span></div>'; for(const n of list){ const div=document.createElement('div'); div.className='item'; div.onclick=()=>openNote(n.source_id); div.innerHTML=`<b>${esc(n.title)}</b><span>${esc(n.subject||'미지정')} · ${esc(n.source_type)} · ${esc(n.source_id)}</span>`; $('list').appendChild(div);} status('목록 불러옴'); }catch(e){status('오류'); alert(e.message);} }
async function openNote(id){ try{ const data=await api('/study/notes/'+encodeURIComponent(id),{headers:headers(false)}); currentSourceId=id; currentSourceType=data.source?.source_type||'generated_note'; $('title').value=data.source?.title||''; $('markdown').value=data.markdown||''; render($('markdown').value); status('열림: '+id); }catch(e){alert(e.message)} }
function newNote(type){ currentSourceId=''; currentSourceType=type; $('title').value=type==='exam_cram'?'시험 직전 정리':'새 정리본'; $('markdown').value= type==='exam_cram' ? '# 시험 직전 정리\n\n## 1. 직전 암기\n\n## 2. 오답 주의사항\n\n## 3. 주요 개념\n\n## 4. 마지막 확인\n' : '# 새 정리본\n\n내용을 입력하세요. 수식은 $...$ 또는 $$...$$로 작성합니다.\n'; render($('markdown').value); status('새 문서'); }
async function saveNote(){ try{ const payload={title:$('title').value.trim()||'Untitled',content_markdown:$('markdown').value,change_summary:'edited in Study Note Studio'}; let data; if(currentSourceId){ data=await api('/study/notes/'+encodeURIComponent(currentSourceId),{method:'PUT',headers:headers(),body:JSON.stringify(payload)}); } else { data=await api('/study/notes',{method:'POST',headers:headers(),body:JSON.stringify({...payload,subject:subject(),source_type:currentSourceType,replace_latest:false})}); currentSourceId=data.source_id; } status('저장됨'); await listNotes(); return data; }catch(e){status('오류'); alert(e.message);} }
function wrapSelection(before,after){ const ta=$('markdown'); const s=ta.selectionStart,e=ta.selectionEnd; const text=ta.value.slice(s,e)||'강조할 내용'; ta.setRangeText(before+text+after,s,e,'end'); onEdit(); }
function highlightSelection(){ wrapSelection('<mark>','</mark>'); }
function insertImage(ev){ const file=ev.target.files?.[0]; if(!file) return; const reader=new FileReader(); reader.onload=()=>{ const name=file.name.replace(/[\]\)]/g,''); wrapSelection(`\n![${name}](${reader.result})\n`,''); }; reader.readAsDataURL(file); ev.target.value=''; }
function downloadMd(){ if(!currentSourceId) return alert('먼저 저장하세요.'); location.href='/study/notes/'+encodeURIComponent(currentSourceId)+'/download.md'; }
function downloadDocx(){ if(!currentSourceId) return alert('먼저 저장하세요.'); location.href='/study/notes/'+encodeURIComponent(currentSourceId)+'/download.docx'; }
function printPdf(){ if(!currentSourceId) return alert('먼저 저장하세요.'); window.open('/study/notes/'+encodeURIComponent(currentSourceId)+'/print','_blank'); }
$('markdown').addEventListener('input',onEdit); restore(); render(''); listNotes();
