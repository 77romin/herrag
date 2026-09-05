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
(async()=>{
 assert.equal(ids.samples.children.length,5);
 await ids.samples.children[0].click();
 assert.equal(ids.start.disabled,false);assert.equal(state('revision'),null);
 await ids['upload-form'].fire('submit');
 assert.equal(state('revision'),'revision-1');assert.equal(ids.input.disabled,false);
 const firstHistory=ids.chat.children.length;
 await ids.samples.children[1].click();uploadFail=true;
 await ids['upload-form'].fire('submit');
 assert.equal(state('revision'),'revision-1');assert.equal(ids.chat.children.length,firstHistory);assert.equal(ids.title.textContent,'베네치아 이야기');uploadFail=false;
 ids.input.value='여기 인천 곱창집 가자';grounding='contradiction';
 await ids['chat-form'].fire('submit');
 assert.ok(ids.chat.children.at(-1).className.includes('warning'));assert.equal(state('revision'),'revision-1');
 ids.input.value='재시도할 대사';chatFail=true;const before=ids.chat.children.length;
 await ids['chat-form'].fire('submit');assert.equal(ids.chat.children.length,before);assert.equal(ids.input.value,'재시도할 대사');chatFail=false;
 grounding='supported';end=true;await ids['chat-form'].fire('submit');
 assert.equal(state('revision'),null);assert.equal(ids.input.disabled,true);assert.equal(state('selectedPack'),null);assert.equal(ids.chat.children.at(-1).className,'ending');
 await ids.samples.children[2].click();await ids['upload-form'].fire('submit');
 assert.equal(ids.chat.children.length,2);assert.equal(ids.title.textContent,'베네치아 이야기');
 await ids.reset.click();assert.equal(state('revision'),null);assert.equal(ids.chat.children.length,1);
 console.log('PASS: 5 packs, selection, start, failed replacement preserves game, contradiction badge, failed reply retry, ending reset, new pack clears history, eject.');
})().catch(e=>{console.error(e);process.exitCode=1;});
