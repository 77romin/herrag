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
(async () => {
 const split = text => Array.from(state('splitSentences(' + JSON.stringify(text) + ')'));
 assert.deepEqual(split('오랜만이야! 여기서 만날 줄 몰랐어. 혹시 혼자 여행 왔어?'), ['오랜만이야!', '여기서 만날 줄 몰랐어.', '혹시 혼자 여행 왔어?']);
 assert.deepEqual(split('그녀가 웃는다. “반가워! 혼자 왔어?”'), ['그녀가 웃는다.', '“반가워!', '혼자 왔어?”']);
 assert.deepEqual(split('3.5유로야. 괜찮지?'), ['3.5유로야.', '괜찮지?']);
 assert.deepEqual(split('고개를 끄덕인다.\n\n반가워'), ['고개를 끄덕인다.', '반가워']);
 assert.deepEqual(split('   '), []);
 await ids.samples.children[0].click();
 data.answer = '오랜만이야! 여기서 만날 줄 몰랐어. 혼자 왔어?';
 const starting = ids['upload-form'].fire('submit');
 await new Promise(resolve => setTimeout(resolve, 30));
 assert.equal(ids.chat.children.length, 1);
 assert.equal(ids.input.disabled, true);
 assert.equal(ids.start.disabled, true);
 assert.equal(ids.chat.children[0].children.length, 2);
 await new Promise(resolve => setTimeout(resolve, 620));
 assert.equal(ids.chat.children.length, 2);
 assert.equal(ids.input.disabled, true);
 await starting;
 assert.equal(ids.chat.children.length, 3);
 assert.equal(ids.chat.children.at(-1).children.length, 3);
 assert.equal(ids.input.disabled, false);
 ids.input.value = '반가워. 나 혼자 왔어.';
 end = true;
 const chatting = ids['chat-form'].fire('submit');
 await new Promise(resolve => setTimeout(resolve, 30));
 assert.equal(ids.chat.children.filter(x => x.className === 'message user').length, 1);
 assert.equal(ids.chat.children.some(x => x.className === 'ending'), false);
 assert.equal(state('busy'), true);
 await chatting;
 assert.equal(ids.chat.children.at(-1).className, 'ending');
 assert.equal(state('revision'), null);
 assert.equal(ids.input.disabled, true);
 console.log('PASS: Korean sentences, quotes, decimals, line breaks, 600ms sequential bubbles, metadata only on last bubble, locked input, single user bubble, ending after last sentence.');
})().catch(error => { console.error(error); process.exitCode = 1; });
