const API = 'http://localhost:8000';
const session = crypto.randomUUID();
const $ = id => document.getElementById(id);
let revision = null;
let busy = false;
let selectedPack = null;
let activeTitle = '';
let heroineName = '상대방';
let cartridgeAnimation = null;
const packs = [
  { file: '이탈리아 베네치아에서 우연히 만난 초등학교 동창', title: '베네치아에서 만난 동창', tag: 'VENICE · 우연한 재회', symbol: '❦', color: '#97584b' },
  { file: '제주 게스트하우스의 마지막 저녁', title: '제주의 마지막 저녁', tag: 'JEJU · 느리게 물드는 마음', symbol: '☀', color: '#a88649' },
  { file: '교토에서 바뀐 필름 카메라', title: '교토에서 바뀐 카메라', tag: 'KYOTO · 필름 속의 설렘', symbol: '▣', color: '#788268' },
  { file: '심야 라디오의 마지막 게스트', title: '심야 라디오의 게스트', tag: 'SEOUL · 주파수 너머의 너', symbol: '☾', color: '#7e7083' },
  { file: '비 오는 북카페의 마지막 페이지', title: '북카페의 마지막 페이지', tag: 'BUSAN · 비와 책, 그리고 우리', symbol: '▤', color: '#987750' }
];

for (const pack of packs) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'pack-card';
  card.dataset.file = pack.file;
  card.setAttribute('aria-label', `${pack.title} 스토리팩 선택`);
  card.setAttribute('aria-pressed', 'false');
  card.style.setProperty('--pack-color', pack.color);
  const icon = document.createElement('span');
  icon.className = 'mini-cart';
  icon.setAttribute('aria-hidden', 'true');
  const symbol = document.createElement('span');
  symbol.textContent = pack.symbol;
  icon.append(symbol);
  const copy = document.createElement('span');
  copy.className = 'pack-card-copy';
  const title = document.createElement('strong');
  title.textContent = pack.title;
  const tag = document.createElement('small');
  tag.textContent = pack.tag;
  copy.append(title, tag);
  const arrow = document.createElement('span');
  arrow.className = 'pack-arrow';
  arrow.textContent = '↗';
  arrow.setAttribute('aria-hidden', 'true');
  card.append(icon, copy, arrow);
  card.addEventListener('click', () => selectLibraryPack(pack));
  $('samples').append(card);
}

function controls(value) {
  busy = value;
  for (const id of ['file', 'choose-file']) {
    const element = $(id);
    if (element) element.disabled = value;
  }
  document.querySelectorAll('.pack-card, .ending button').forEach(el => el.disabled = value);
  $('start').disabled = value || !selectedPack;
  if ($('welcome-start')) $('welcome-start').disabled = value || !selectedPack;
  for (const id of ['input', 'send', 'reset']) $(id).disabled = value || !revision;
  document.querySelector('.screen-panel').setAttribute('aria-busy', String(value));
  $('upload-form').setAttribute('aria-busy', String(value));
}

function status(text = '', error = false) {
  $('status').textContent = text;
  $('status').classList.toggle('error', error);
}

function selectPack(file, pack) {
  const fileTitle = file.name.replace(/\.(md|txt|pdf)$/i, '');
  // A downloaded library pack keeps its original color when opened as a file.
  pack = pack || packs.find(item => item.file === fileTitle);
  const colorIndex = Array.from(fileTitle).reduce((hash, character) =>
    (hash * 31 + character.codePointAt(0)) >>> 0, 0) % packs.length;
  const color = pack?.color || packs[colorIndex].color;
  selectedPack = file;
  $('cartridge').style.setProperty('--inserted-pack-color', color);
  $('cartridge').classList.add('loaded');
  $('pack-title').textContent = pack?.title || fileTitle;
  $('pack-subtitle').textContent = '선택 완료 · 시작을 눌러주세요';
  $('pack-symbol').textContent = pack?.symbol || '♥';
  document.querySelectorAll('.pack-card').forEach(card => {
    const selected = card.dataset.file === pack?.file;
    card.classList.toggle('selected', selected);
    card.setAttribute('aria-pressed', String(selected));
  });
  cartridgeAnimation?.cancel();
  cartridgeAnimation = null;
  $('pack-slot').scrollIntoView({ block: 'nearest', behavior: 'instant' });
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    cartridgeAnimation = $('cartridge').animate([
      { transform: 'translateY(-115%) rotate(-3deg)', opacity: 0, offset: 0 },
      { transform: 'translateY(-85%) rotate(-2deg)', opacity: 1, offset: 0.18 },
      { transform: 'translateY(4px) rotate(0deg)', opacity: 1, offset: 0.8 },
      { transform: 'translateY(0) rotate(0deg)', opacity: 1, offset: 1 }
    ], { duration: 700, easing: 'cubic-bezier(.2,.7,.25,1)' });
  }
}

async function selectLibraryPack(pack) {
  if (busy) return;
  controls(true);
  status('보관함에서 스토리팩을 꺼내고 있어요…');
  try {
    const response = await fetch(`sample_data/${encodeURIComponent(pack.file)}.md`);
    if (!response.ok) throw new Error('스토리팩을 찾지 못했어요. 파일 경로를 확인해 주세요.');
    const content = await response.blob();
    selectPack(new File([content], `${pack.file}.md`, { type: 'text/markdown' }), pack);
    $('file').value = '';
    status(revision ? '팩을 선택했어요. 시작하면 현재 이야기가 새 이야기로 바뀝니다.' : '팩을 선택했어요. ‘이 팩으로 시작’을 눌러주세요.');
  } catch (error) {
    status(error.message || '스토리팩을 읽지 못했어요.', true);
  } finally {
    controls(false);
    if (selectedPack) $('start').focus({ preventScroll: true });
  }
}

function chooseFile() {
  if (!busy) {
    // Keep selectedPack separately, allowing the same file to be inserted again.
    $('file').value = '';
    $('file').click();
  }
}
$('choose-file').addEventListener('click', chooseFile);
$('welcome-start').addEventListener('click', () => {
  if (!busy && selectedPack) $('upload-form').requestSubmit();
});
$('file').addEventListener('change', () => {
  const file = $('file').files[0];
  if (!file) return;
  if (!/\.(md|txt|pdf)$/i.test(file.name) || !file.size || file.size > 2 * 1024 * 1024) {
    $('file').value = '';
    status('비어 있지 않은 2MB 이하의 MD, TXT, PDF 스토리팩을 선택해 주세요.', true);
    return;
  }
  selectPack(file);
  status('스토리팩 준비 완료. 시작 버튼을 누르면 새 이야기가 펼쳐집니다.');
  controls(false);
});

function message(type, text, notice, evidence, warning = false) {
  const div = document.createElement('div');
  div.className = `message ${type} has-profile${warning ? ' warning' : ''}`;
  const avatar = document.createElement('span');
  avatar.className = 'message-avatar';
  const portrait = document.createElement('img');
  portrait.src = type === 'user' ? 'assets/profiles/male.png' : 'assets/profiles/female.png';
  portrait.alt = type === 'user' ? '남자 주인공 프로필' : `${heroineName} 프로필`;
  portrait.width = 44;
  portrait.height = 44;
  avatar.append(portrait);
  const content = document.createElement('div');
  content.className = 'message-content';
  const role = document.createElement('span');
  role.className = 'message-role';
  role.textContent = type === 'user' ? 'YOU / 나의 대사' : heroineName;
  const body = document.createElement('div');
  body.className = 'message-body';
  body.textContent = text;
  content.append(role, body);
  div.append(avatar, content);
  if (notice) {
    const small = document.createElement('small');
    small.textContent = notice;
    content.append(small);
  }
  if (evidence) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = '스토리팩의 설정 근거 보기';
    const quote = document.createElement('p');
    quote.textContent = evidence;
    details.append(summary, quote);
    content.append(details);
  }
  $('chat').append(div);
  scrollChat();
  return div;
}

// Keep punctuation and closing quotes with the sentence they belong to.
const sentenceSegmenter = typeof Intl.Segmenter === 'function'
  ? new Intl.Segmenter('ko', { granularity: 'sentence' })
  : null;

function splitSentences(text) {
  return String(text ?? '').split(/\r?\n+/).flatMap(line => {
    if (sentenceSegmenter) {
      return Array.from(sentenceSegmenter.segment(line), part => part.segment.trim());
    }
    // Fallback: split after sentence punctuation, not inside decimals or URLs.
    return line.split(/(?<=[.!?。！？…][”’"')\]]*)\s+(?=\S)/).map(part => part.trim());
  }).filter(Boolean);
}

async function showStoryReply(data, notice, evidence, warning = false) {
  const segments = Array.isArray(data.segments) && data.segments.length
    ? data.segments
    : [{ kind: 'narration', text: data.answer }];
  const parts = segments.flatMap(part => part.kind === 'dialogue'
    ? splitSentences(part.text).map(text => ({ kind: 'dialogue', text }))
    : [{ kind: 'narration', text: part.text }]);
  status(`${heroineName}의 이야기가 이어지고 있어요…`);
  // The response has arrived; let assistive technology announce each new bubble.
  document.querySelector('.screen-panel').setAttribute('aria-busy', 'false');
  for (let index = 0; index < parts.length; index += 1) {
    if (index > 0) await new Promise(resolve => setTimeout(resolve, 600));
    const part = parts[index];
    if (part.kind === 'dialogue') {
      message('bot', part.text, null, null, warning);
    } else {
      const paragraph = document.createElement('p');
      paragraph.className = 'story-narration';
      paragraph.textContent = part.text;
      $('chat').append(paragraph);
      scrollChat();
    }
  }
  // Metadata belongs to the complete reply, even when its last part is narration.
  if (notice || evidence) {
    const footer = document.createElement('div');
    footer.className = `reply-context${warning ? ' warning' : ''}`;
    if (notice) {
      const label = document.createElement('small');
      label.textContent = notice;
      footer.append(label);
    }
    if (evidence) {
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = '스토리팩의 설정 근거 보기';
      const quote = document.createElement('p');
      quote.textContent = evidence;
      details.append(summary, quote);
      footer.append(details);
    }
    $('chat').append(footer);
    scrollChat();
  }
}

function scrollChat() { $('chat').scrollTop = $('chat').scrollHeight; }
function updateCounter() { $('char-count').textContent = `${$('input').value.length.toLocaleString()} / 2,000`; }
$('input').addEventListener('input', updateCounter);
function progress(number = 0, total = 1) {
  const percent = Math.max(0, Math.min(100, Math.round(number / total * 100)));
  $('progress').setAttribute('aria-valuenow', String(percent));
  $('progress').firstElementChild.style.width = `${percent}%`;
}
function updateScene(data) {
  $('scene').textContent = `CHAPTER ${String(data.scene_number).padStart(2, '0')} / ${String(data.scene_count).padStart(2, '0')} · ${data.scene}`;
  progress(data.scene_number, data.scene_count);
}

function showBrief(brief) {
  const facts = $('brief-facts');
  facts.replaceChildren();
  const labels = { location: '장소와 시간', player: '나의 역할', heroine: '상대 인물', relationship: '우리의 관계', situation: '지금의 상황' };
  for (const [key, label] of Object.entries(labels)) {
    const text = brief?.[key];
    if (typeof text !== 'string' || !text.trim()) continue;
    const term = document.createElement('dt');
    term.textContent = label;
    const description = document.createElement('dd');
    description.textContent = text;
    facts.append(term, description);
  }
  $('brief-empty').hidden = facts.children.length > 0;
  $('story-brief').hidden = false;
}

async function request(path, options) {
  let response;
  try { response = await fetch(API + path, options); }
  catch { throw new Error('서버에 연결하지 못했어요. 서버 실행 상태를 확인하고 다시 시도해 주세요.'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : '요청을 처리하지 못했어요. 다시 시도해 주세요.');
    error.status = response.status;
    throw error;
  }
  return data;
}
const post = (path, body) => request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function clearState(ended = false) {
  cartridgeAnimation?.cancel();
  cartridgeAnimation = null;
  revision = null;
  selectedPack = null;
  activeTitle = '';
  heroineName = '상대방';
  $('story-brief').hidden = true;
  $('brief-facts').replaceChildren();
  $('title').textContent = ended ? '우리 이야기의 마지막 장' : '다음 이야기를 기다리는 중';
  $('scene').textContent = '진행 상태가 초기화됐어요. 새 스토리팩을 넣어주세요.';
  $('input').value = '';
  $('input').placeholder = '새 스토리팩을 넣어 다음 이야기를 시작하세요.';
  $('file').value = '';
  $('cartridge').classList.remove('loaded');
  $('pack-title').textContent = '다음 이야기를 기다려요';
  $('pack-subtitle').textContent = '새로운 스토리팩을 넣어주세요';
  $('pack-symbol').textContent = '♡';
  $('power-led').classList.remove('on');
  $('power-label').textContent = '대기 중';
  $('playing-label').textContent = ended ? 'STORY COMPLETE' : 'READY TO PLAY';
  document.querySelectorAll('.pack-card').forEach(card => { card.classList.remove('selected'); card.setAttribute('aria-pressed', 'false'); });
  progress();
  updateCounter();
}

function endingCard(title) {
  const div = document.createElement('div');
  div.className = 'ending';
  const label = document.createElement('span');
  label.className = 'ending-label';
  label.textContent = '♥ THE END ♥';
  const heading = document.createElement('h3');
  heading.textContent = title;
  const text = document.createElement('p');
  text.textContent = '이 이야기는 여기서 잠시 안녕.\n진행 상태가 초기화되었어요. 다음 우연을 만나볼까요?';
  const button = document.createElement('button');
  button.className = 'welcome-start';
  button.textContent = '새 스토리팩 삽입 ↗';
  button.addEventListener('click', chooseFile);
  div.append(label, heading, text, button);
  $('chat').append(div);
  scrollChat();
}

$('upload-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !selectedPack) return;
  controls(true);
  status('저장된 스토리팩 확인 중… 처음 넣는 팩은 준비에 시간이 걸릴 수 있어요.');
  const form = new FormData();
  form.append('file', selectedPack);
  form.append('session_id', session);
  try {
    const data = await request('/upload', { method: 'POST', body: form });
    revision = data.revision;
    activeTitle = data.title;
    heroineName = typeof data.heroine_name === 'string' && data.heroine_name.trim()
      ? data.heroine_name.trim() : '상대방';
    $('chat').replaceChildren();
    $('input').value = '';
    $('input').placeholder = '어떤 말을 건넬까요? 대사나 행동을 입력하세요…';
    $('title').textContent = data.title;
    $('power-led').classList.add('on');
    $('power-label').textContent = '플레이 중';
    $('playing-label').textContent = 'NOW PLAYING';
    $('pack-subtitle').textContent = '지금 플레이 중인 스토리팩';
    showBrief(data.brief);
    updateScene(data);
    updateCounter();
    await showStoryReply(data, `스토리팩 참고 · ${data.source}`);
    status(data.cache_hit
      ? '저장된 스토리팩으로 시작했어요. 당신의 첫 대사를 들려주세요.'
      : '새 스토리팩 준비 완료. 다음부터는 저장된 팩으로 바로 시작해요.');
  } catch (error) {
    status(`${error.message}${revision ? ' 현재 이야기는 유지됩니다.' : ''}`, true);
  } finally {
    controls(false);
    if (revision) $('input').focus();
  }
});

$('chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  const text = $('input').value.trim();
  if (!text || !revision || busy) return;
  controls(true);
  status('이야기 속 그녀가 답장을 쓰고 있어요…');
  const userBubble = message('user', text);
  const pending = message('bot pending', '잠시만 기다려주세요');
  try {
    const data = await post('/story/chat', { session_id: session, revision, message: text });
    pending.remove();
    const warning = data.grounding === 'contradiction' || data.grounding === 'unspecified';
    const notice = data.grounding === 'contradiction'
      ? '스토리 설정과 맞지 않아요 · 문서 근거 없음 · 진행 유지'
      : data.grounding === 'unspecified'
        ? '스토리팩에서 확인할 수 없어요 · 문서 근거 없음 · 일반 AI 반응 · 진행 유지'
        : '스토리팩 참고';
    await showStoryReply(data, `${notice} · ${data.source}`, data.evidence, warning);
    $('input').value = '';
    updateCounter();
    updateScene(data);
    status();
    if (data.ended) {
      endingCard(data.ending_title);
      clearState(true);
    }
  } catch (error) {
    pending.remove();
    userBubble.remove();
    status(error.message, true);
    if (error.status === 409) clearState();
  } finally {
    controls(false);
    if (revision) $('input').focus();
  }
});

$('input').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $('chat-form').requestSubmit();
  }
});

$('reset').addEventListener('click', async () => {
  if (busy || !revision) return;
  controls(true);
  status('스토리팩을 꺼내고 있어요…');
  try {
    await post('/story/reset', { session_id: session });
    const previousTitle = activeTitle;
    clearState();
    $('chat').replaceChildren();
    message('bot', `‘${previousTitle}’ 팩을 꺼냈어요.\n새 스토리팩을 넣어 다른 이야기를 시작해 보세요.`);
    status();
  } catch (error) {
    status(error.message, true);
  } finally { controls(false); }
});
