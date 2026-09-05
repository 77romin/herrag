const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const elements = [];
class Element {
  constructor(tag='div') { this.tagName=tag;this.children=[];this.events={};this.attributes={};this.dataset={};this.style={setProperty(){}};this.className='';this.textContent='';this.value='';this.disabled=false;this.files=[];elements.push(this);this.classList={add:(c)=>{if(!this.className.split(' ').includes(c))this.className+=' '+c;},remove:(c)=>{this.className=this.className.split(' ').filter(x=>x!==c).join(' ');},toggle:(c,v)=>{const on=v??!this.className.split(' ').includes(c);on?this.classList.add(c):this.classList.remove(c);}}; }
  append(...nodes){nodes.forEach(n=>{n.parent=this;this.children.push(n);});}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  setAttribute(k,v){this.attributes[k]=v;}
  addEventListener(k,fn){this.events[k]=fn;}
  focus(){}
  click(){return this.fire('click');}
  fire(k){return this.events[k]?.({preventDefault(){}});}
  get firstElementChild(){return this.children[0];}
}
const html=fs.readFileSync('clients/index.html','utf8');
const ids=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
ids.progress.append(new Element());
const screen = new Element();
const document={getElementById:id=>ids[id]||null,createElement:tag=>new Element(tag),querySelector:s=>s==='.screen-panel'?screen:null,querySelectorAll:s=>elements.filter(e=>e.className.split(' ').includes('pack-card')||(s.includes('.ending button')&&e.tagName==='button'&&e.parent?.className==='ending'))};
let uploadFail=false,chatFail=false,end=false,grounding='supported',lastRequest;
const data={revision:'revision-1',title:'베네치아 이야기',scene:'재회',scene_number:1,scene_count:4,answer:'오랜만이야.',source:'베네치아.md'};
const context=vm.createContext({document,crypto:{randomUUID:()=> 'session-1'},File,FormData,Blob,console,fetch:async(url,opts)=>{lastRequest={url,opts};if(url.startsWith('sample_data/'))return {ok:true,blob:async()=>new Blob(['# sample'])};if(url.endsWith('/upload'))return {ok:!uploadFail,status:502,json:async()=>uploadFail?{detail:'업로드 실패'}:data};if(url.endsWith('/story/chat'))return {ok:!chatFail,status:502,json:async()=>chatFail?{detail:'응답 실패'}:{...data,grounding,ended:end,ending_title:'다음 약속',evidence:grounding==='contradiction'?'현재 베네치아다.':null}};return {ok:true,json:async()=>({success:true})};}});
vm.runInContext(fs.readFileSync('clients/script.js','utf8'),context);
const state = expr=>vm.runInContext(expr,context);

context.setTimeout = setTimeout;
(async()=>{
 state('heroineName="한서윤"');
 const data={segments:[{kind:'narration',text:'늦은 오후. 서윤이 다가온다.'},{kind:'dialogue',text:'오랜만이야! 혼자 왔어?'},{kind:'narration',text:'서윤이 웃는다.'}]};
 const run=state('showStoryReply('+JSON.stringify(data)+',"스토리팩 참고","실제 근거",true)');
 await new Promise(r=>setTimeout(r,30));
 assert.equal(ids.chat.children.length,1);
 assert.equal(ids.chat.children[0].className,'story-narration');
 assert.equal(ids.chat.children[0].children.length,0);
 await run;
 assert.equal(ids.chat.children.length,5);
 assert.equal(ids.chat.children[1].children[1].children[0].textContent,'한서윤');
 assert.equal(ids.chat.children[1].children[1].children[1].textContent,'오랜만이야!');
 assert.equal(ids.chat.children[2].children[1].children[1].textContent,'혼자 왔어?');
 assert.equal(ids.chat.children[3].className,'story-narration');
 assert.equal(ids.chat.children[4].className,'reply-context warning');
 assert.equal(ids.chat.children[4].children.length,2);
 const before=ids.chat.children.length;
 state('message("user","내 대사. 두 문장.")');
 assert.equal(ids.chat.children.length,before+1);
 state('cartridgeAnimation=null;clearState()');
 assert.equal(state('heroineName'),'상대방');
 console.log('PASS: ordered narration/dialogue, sentence bubbles, dynamic heroine name, single metadata footer, unchanged user bubble, name reset.');
})().catch(e=>{console.error(e);process.exitCode=1;});
