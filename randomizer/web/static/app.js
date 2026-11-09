'use strict';
(function () {
  const $ = (id) => document.getElementById(id);
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));

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

  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    };
    const r = await fetch(path, opts);
    return r.json();
  }

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

  async function validate() {
    const p = $('nup').value.trim();
    const st = $('nup-status');
    if (!p) { setStatus(st, ''); return; }
    try {
      const r = await api('/api/validate', { nup_path: p });
      if (r.ok) setStatus(st, '✔ Versión ' + r.version + ' detectada', 'ok');
      else setStatus(st, r.error || 'Error de validación.', 'err');
    } catch (e) {
      setStatus(st, 'No se pudo contactar con el servidor.', 'err');
    }
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
      if (!it.movable) {
        cb.disabled = true;
        cb.checked = false;
        lab.classList.add('disabled');
        const s = document.createElement('span');
        s.textContent = '(fijo en esta versión)';
        lab.appendChild(s);
      }
      box.appendChild(lab);
    });
  }

  function excludedList() {
    return Array.from($('items').querySelectorAll('input:checked:not(:disabled)')).map((c) => c.value);
  }

  let spoilerPath = null;
  function showSpoilerLink(path) {
    spoilerPath = path || null;
    $('spoiler-link').hidden = !spoilerPath;
    $('spoiler-text').hidden = true;
    $('spoiler-text').textContent = '';
  }

  async function generate(overwrite) {
    const btn = $('generate');
    const res = $('result');
    btn.disabled = true;
    btn.textContent = 'Generando…';
    setStatus(res, '');
    let retry = false;
    try {
      const seed = $('seed').value.trim();
      const r = await api('/api/generate', {
        nup_path: $('nup').value.trim(), out_dir: $('outdir').value.trim(), seed: seed,
        key_items_mode: $('mode').value, excluded_items: excludedList(),
        spoiler: $('spoiler').checked, overwrite: !!overwrite,
      });
      if (r.ok) {
        setStatus(res, '✔ Mod Rando_' + r.seed + ' creado en ' + r.mod_dir +
          '. Desactiva otros mods Rando_* de este juego en Lichii.', 'ok');
        $('seed').value = r.seed;
        showSpoilerLink(r.spoiler_txt);
      } else if (r.exists && !overwrite) {
        retry = window.confirm('Ya existe Rando_' + seed + '. ¿Sobrescribir?');
      } else {
        setStatus(res, r.error || 'Error desconocido.', 'err');
      }
    } catch (e) {
      setStatus(res, 'No se pudo contactar con el servidor.', 'err');
    }
    btn.disabled = false;
    btn.textContent = 'Generar';
    if (retry) return generate(true);
  }

  $('spoiler-link').addEventListener('click', async (e) => {
    e.preventDefault();
    if (!spoilerPath) return;
    const pre = $('spoiler-text');
    try {
      const r = await fetch('/api/spoiler?path=' + encodeURIComponent(spoilerPath));
      if (r.ok) pre.textContent = await r.text();
      else pre.textContent = (await r.json()).error || 'No se pudo cargar el registro.';
    } catch (err) {
      pre.textContent = 'No se pudo cargar el registro.';
    }
    pre.hidden = false;
  });

  $('nup').addEventListener('blur', validate);
  $('dice').addEventListener('click', () => { $('seed').value = randomSeed(); });
  $('generate').addEventListener('click', () => generate(false));

  async function init() {
    let cfg = {};
    try { cfg = await api('/api/config'); } catch (e) { /* sin config */ }
    const ls = cfg.last_settings || {};
    if (cfg.nup_path) { $('nup').value = cfg.nup_path; validate(); }
    if (cfg.out_dir) $('outdir').value = cfg.out_dir;
    $('seed').value = ls.seed || randomSeed();
    if (ls.key_items_mode === 'vanilla' || ls.key_items_mode === 'any_chest') $('mode').value = ls.key_items_mode;
    if (typeof ls.spoiler === 'boolean') $('spoiler').checked = ls.spoiler;
    try {
      renderItems(await api('/api/items'), Array.isArray(ls.excluded_items) ? ls.excluded_items : []);
    } catch (e) {
      $('items').textContent = 'No se pudo cargar la lista de objetos.';
    }
  }
  init();
})();
