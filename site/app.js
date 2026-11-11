'use strict';
(function () {
  const $ = (id) => document.getElementById(id);
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  const STORE = 'oot-remake-rando-settings';
  const TOKENSANITY = ['off', 'dungeons', 'overworld', 'all'];

  function selectTab(tab, focus) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      $(t.getAttribute('aria-controls')).hidden = !on;
    });
    if (focus) tab.focus();
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => selectTab(t, false));
    t.addEventListener('keydown', (e) => {
      let j = null;
      if (e.key === 'ArrowRight') j = (i + 1) % tabs.length;
      else if (e.key === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
      else if (e.key === 'Home') j = 0;
      else if (e.key === 'End') j = tabs.length - 1;
      if (j !== null) { e.preventDefault(); selectTab(tabs[j], true); }
    });
  });

  function setStatus(el, text, cls) {
    el.textContent = text;
    el.className = 'status' + (cls ? ' ' + cls : '');
  }

  function randomSeed() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const a = new Uint32Array(10);
    crypto.getRandomValues(a);
    return Array.from(a, (n) => chars[n % chars.length]).join('');
  }

  // ---- saved settings (per browser; never required) ----
  function loadSaved() {
    try { return JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch (e) { return {}; }
  }
  function save(options) {
    try { localStorage.setItem(STORE, JSON.stringify(options)); } catch (e) { /* storage blocked */ }
  }

  function renderItems(items, excluded) {
    const box = $('items');
    box.textContent = '';
    items.forEach((it) => {
      const lab = document.createElement('label');
      lab.className = 'check';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = it.actor;
      cb.checked = excluded.includes(it.actor);
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(' ' + it.label));
      if (!it.movable || it.excludable === false) {
        cb.disabled = true;
        cb.checked = false;
        lab.classList.add('disabled');
        const s = document.createElement('span');
        s.textContent = it.movable ? ' (required by the logic)' : ' (fixed in this version)';
        lab.appendChild(s);
      }
      box.appendChild(lab);
    });
  }

  function options() {
    return {
      seed: $('seed').value.trim(),
      key_items_mode: $('mode').value,
      excluded_items: Array.from($('items').querySelectorAll('input:checked:not(:disabled)')).map((c) => c.value),
      spoiler: $('spoiler').checked,
      skip_cutscenes: $('skip-cutscenes').checked,
      tokensanity: $('tokensanity').value,
    };
  }

  // ---- worker ----
  let engineReady = false;
  let nupOk = false;
  let busy = false;
  function refreshButton() {
    $('generate').disabled = !(engineReady && nupOk) || busy;
  }

  const saved = loadSaved();
  $('seed').value = typeof saved.seed === 'string' && saved.seed ? saved.seed : randomSeed();
  if (saved.key_items_mode === 'vanilla' || saved.key_items_mode === 'any_chest') $('mode').value = saved.key_items_mode;
  if (typeof saved.spoiler === 'boolean') $('spoiler').checked = saved.spoiler;
  if (typeof saved.skip_cutscenes === 'boolean') $('skip-cutscenes').checked = saved.skip_cutscenes;
  if (TOKENSANITY.includes(saved.tokensanity)) $('tokensanity').value = saved.tokensanity;

  let worker;
  try {
    worker = new Worker('worker.js', { type: 'module' });
  } catch (e) {
    setStatus($('engine'), 'This browser cannot run the randomizer (module workers are not supported).', 'err');
    return;
  }

  function download(name, bytes) {
    const url = URL.createObjectURL(new Blob([bytes], { type: 'application/zip' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  function finish() {
    busy = false;
    $('generate').textContent = 'Generate and download';
    refreshButton();
  }

  worker.onmessage = (ev) => {
    const m = ev.data;
    if (m.type === 'status') {
      setStatus(busy ? $('result') : $('engine'), m.text);
    } else if (m.type === 'ready') {
      engineReady = true;
      setStatus($('engine'), '✔ Randomizer ready.', 'ok');
      renderItems(m.items, Array.isArray(saved.excluded_items) ? saved.excluded_items : []);
      if ($('nup').files.length) checkNup();
      refreshButton();
    } else if (m.type === 'nup') {
      nupOk = !!m.result.ok;
      if (nupOk) setStatus($('nup-status'), '✔ Version ' + m.result.version + ' detected', 'ok');
      else setStatus($('nup-status'), m.result.error || 'This file cannot be used.', 'err');
      setStatus($('engine'), '✔ Randomizer ready.', 'ok');
      refreshButton();
    } else if (m.type === 'done') {
      download(m.name, m.bytes);
      $('seed').value = m.seed;
      setStatus($('result'), '✔ Downloaded ' + m.name + '. Unzip it and copy the Rando_' + m.seed +
        ' folder into load/0400486024DEC000/ in Lichii (see the Install tab).', 'ok');
      finish();
    } else if (m.type === 'error') {
      if (busy) { setStatus($('result'), m.message, 'err'); finish(); }
      else setStatus(engineReady ? $('nup-status') : $('engine'), m.message, 'err');
    }
  };
  worker.onerror = () => {
    setStatus($('engine'), 'The randomizer stopped unexpectedly. Reload the page to try again.', 'err');
    busy = false;
    engineReady = false;
    refreshButton();
  };

  function checkNup() {
    const f = $('nup').files[0];
    nupOk = false;
    refreshButton();
    if (!f) { setStatus($('nup-status'), ''); return; }
    if (!engineReady) { setStatus($('nup-status'), 'The file will be checked when the randomizer is ready.'); return; }
    setStatus($('nup-status'), 'Checking…');
    worker.postMessage({ type: 'nup', file: f });
  }

  $('nup').addEventListener('change', checkNup);
  $('dice').addEventListener('click', () => { $('seed').value = randomSeed(); });
  $('generate').addEventListener('click', () => {
    if (busy) return;
    const o = options();
    if (!o.seed) { o.seed = randomSeed(); $('seed').value = o.seed; }
    save(o);
    busy = true;
    $('generate').textContent = 'Generating…';
    refreshButton();
    setStatus($('result'), 'Generating…');
    worker.postMessage({ type: 'generate', options: o });
  });
})();
