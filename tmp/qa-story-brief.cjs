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

Element.prototype.requestSubmit = function() { return this.fire('submit'); };
context.setTimeout = setTimeout;
(async () => {
 state('controls(false)');
 assert.equal(ids['welcome-start'].disabled, true);
 await ids.samples.children[0].click();
 assert.equal(ids['welcome-start'].disabled, false);
 data.brief = {location:'임의의 항구', player:'여행자', unknown:'스포일러'};
 await ids['welcome-start'].click();
 await new Promise(resolve=>setTimeout(resolve,30));
 assert.equal(state('revision'), 'revision-1');
 assert.equal(ids['story-brief'].hidden, false);
 assert.equal(ids['brief-facts'].children.length, 4);
 assert.equal(ids['brief-facts'].children[1].textContent, '임의의 항구');
 await ids.samples.children[1].click();
 assert.equal(ids['brief-facts'].children[1].textContent, '임의의 항구');
 uploadFail=true;await ids['upload-form'].fire('submit');
 assert.equal(ids['brief-facts'].children[1].textContent, '임의의 항구');
 uploadFail=false;data.brief={situation:'처음 만난 도서관'};
 await ids['upload-form'].fire('submit');
 assert.equal(ids['brief-facts'].children.length,2);
 assert.equal(ids['brief-facts'].children[1].textContent,'처음 만난 도서관');
 await ids.reset.click();
 assert.equal(ids['story-brief'].hidden,true);
 assert.equal(ids['brief-facts'].children.length,0);
 assert.equal(ids['welcome-start'].disabled,true);
 console.log('PASS: start gating/action, custom brief display, whitelist, failed replacement preserves brief, successful replacement and reset.');
})().catch(error=>{console.error(error);process.exitCode=1;});
