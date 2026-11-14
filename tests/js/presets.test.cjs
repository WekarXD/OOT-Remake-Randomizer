'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const Presets = require('../../site/presets.js');

const base = {
  seed: 'S', spoiler: true, excluded_items: [],
  key_items_mode: 'vanilla', tokensanity: 'off', shuffle_songs: 'off', skip_cutscenes: false,
};

test('apply keeps seed and spoiler and clears exclusions', () => {
  const input = { ...base, spoiler: false, excluded_items: ['Item_Hammer'], tokensanity: 'all' };
  assert.deepEqual(Presets.apply(input, 'easy'), {
    seed: 'S', spoiler: false, excluded_items: [],
    key_items_mode: 'any_chest', tokensanity: 'off', shuffle_songs: 'song_locations', skip_cutscenes: true,
  });
});

test('apply does not mutate its input', () => {
  const input = { ...base, excluded_items: ['Item_Hammer'] };
  const copy = structuredClone(input);
  Presets.apply(input, 'hell');
  assert.deepEqual(input, copy);
});

test('apply throws on unknown id', () => {
  assert.throws(() => Presets.apply(base, 'nope'), /Unknown preset: nope/);
});

test('list has the three presets in order', () => {
  assert.deepEqual(Presets.LIST.map((p) => p.id), ['beginner', 'easy', 'hell']);
  assert.deepEqual(Presets.LIST.map((p) => p.label), ['Default / Beginner', 'Easy Mode', 'Hell Mode']);
  assert.deepEqual(Presets.LIST[2].settings,
    { key_items_mode: 'any_chest', tokensanity: 'all', shuffle_songs: 'anywhere', skip_cutscenes: true });
});

test('match finds each preset', () => {
  for (const p of Presets.LIST) assert.equal(Presets.match(Presets.apply(base, p.id)), p.id);
});

test('match returns custom with exclusions', () => {
  assert.equal(Presets.match({ ...Presets.apply(base, 'hell'), excluded_items: ['Item_Hammer'] }), Presets.CUSTOM);
});

test('match returns custom for old saved settings', () => {
  assert.equal(Presets.match(base), 'custom');
});

test('old defaults match beginner', () => {
  assert.equal(Presets.match({ key_items_mode: 'any_chest', tokensanity: 'off', shuffle_songs: 'off', skip_cutscenes: false }),
    'beginner');
});

test('describe gives preset text and a custom fallback', () => {
  assert.equal(Presets.describe('hell'), Presets.LIST[2].description);
  assert.equal(Presets.describe('custom'), 'Your own settings.');
});
