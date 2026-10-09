import assert from 'node:assert/strict';
import test from 'node:test';
import {availableModes, defaultMode, visibleTabs} from '../src/lib/mobileRoles.ts';

test('representative-only users start in their team view without a player profile', () => {
  assert.equal(defaultMode(['team_representative']), 'representative');
  assert.deepEqual(availableModes(['team_representative']), ['representative']);
  assert.deepEqual(visibleTabs('representative'), ['index', 'teams', 'team-games', 'standings', 'profile']);
});

test('every supported cumulative role is available for switching', () => {
  assert.deepEqual(availableModes(['player', 'team_representative', 'referee']), ['referee', 'representative', 'player']);
  assert.equal(defaultMode(['player', 'team_representative']), 'representative');
});

test('unsupported roles have no mobile mode and existing referee tabs stay isolated', () => {
  assert.equal(defaultMode(['league_admin']), null);
  assert.deepEqual(availableModes([]), []);
  assert.deepEqual(visibleTabs('referee'), ['index', 'assignments', 'history', 'profile']);
});
