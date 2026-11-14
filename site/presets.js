// Settings presets: pure data and logic, shared by the page (global `Presets`)
// and the Node tests (module.exports).
(function (root) {
  'use strict';

  const CUSTOM = 'custom';
  const KEYS = ['key_items_mode', 'tokensanity', 'shuffle_songs', 'skip_cutscenes'];

  const LIST = Object.freeze([
    {
      id: 'beginner',
      label: 'Default / Beginner',
      description: 'For players who know the vanilla game and want a similar progression. ' +
        'Key items are shuffled among chests; no timesavers, cutscenes play as usual.',
      settings: { key_items_mode: 'any_chest', tokensanity: 'off', shuffle_songs: 'off', skip_cutscenes: false },
    },
    {
      id: 'easy',
      label: 'Easy Mode',
      description: 'For players who have seen a randomizer before and want to dive right in. ' +
        'Songs are shuffled among the places that teach a song, and cutscenes are skipped.',
      settings: { key_items_mode: 'any_chest', tokensanity: 'off', shuffle_songs: 'song_locations', skip_cutscenes: true },
    },
    {
      id: 'hell',
      label: 'Hell Mode',
      description: 'Everything this version can shuffle, shuffled: every Gold Skulltula can hold an item ' +
        'and songs can be anywhere. Still always beatable. Expect a long playthrough and take notes.',
      settings: { key_items_mode: 'any_chest', tokensanity: 'all', shuffle_songs: 'anywhere', skip_cutscenes: true },
    },
  ].map((p) => Object.freeze({ ...p, settings: Object.freeze(p.settings) })));

  function find(id) {
    return LIST.find((p) => p.id === id);
  }

  function apply(options, id) {
    const preset = find(id);
    if (!preset) throw new Error('Unknown preset: ' + id);
    return { ...options, ...preset.settings, excluded_items: [] };
  }

  function match(options) {
    const excluded = options.excluded_items || [];
    if (excluded.length) return CUSTOM;
    const hit = LIST.find((p) => KEYS.every((k) => options[k] === p.settings[k]));
    return hit ? hit.id : CUSTOM;
  }

  function describe(id) {
    const preset = find(id);
    return preset ? preset.description : 'Your own settings.';
  }

  const api = Object.freeze({ LIST, CUSTOM, apply, match, describe });
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Presets = api;
})(this);
