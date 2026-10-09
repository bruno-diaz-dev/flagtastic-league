import assert from 'node:assert/strict';
import test from 'node:test';
import { chronological, gameState } from '../src/lib/referee.ts';

test('postponed games stay out of history even with recorded scores', () => {
  assert.equal(gameState({status: 'postponed', home_score: 0, away_score: 0}), 'postponed');
});
test('zero scores count as a result; incomplete scores do not', () => {
  assert.equal(gameState({status: 'scheduled', home_score: 0, away_score: 0}), 'completed');
  assert.equal(gameState({status: 'scheduled', home_score: 0, away_score: null}), 'pending');
  assert.equal(gameState({status: 'completed', home_score: null, away_score: null}), 'completed');
});
test('agenda sorts by jornada and time with unconfirmed times last', () => {
  const games = [
    {id: 3, week: 2, start_time: null},
    {id: 2, week: 2, start_time: '09:00:00'},
    {id: 1, week: 1, start_time: '13:00:00'},
    {id: 4, week: 2, start_time: '08:00:00'},
  ];
  assert.deepEqual([...games].sort(chronological).map(game => game.id), [1, 4, 2, 3]);
});
