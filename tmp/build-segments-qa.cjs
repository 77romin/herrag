const fs = require('fs');
const source = fs.readFileSync('tmp/qa-story-ui.cjs', 'utf8');
const prefix = source.slice(0, source.indexOf('(async()=>{'));
fs.writeFileSync('tmp/qa-story-segments.cjs', prefix + `
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
`);
