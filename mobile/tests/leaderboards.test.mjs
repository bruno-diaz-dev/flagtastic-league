import assert from 'node:assert/strict';
import test from 'node:test';
import {podiumLeaders, rankLeaders} from '../src/lib/leaderboards.ts';

test('podium puts third on the left, first in the center and second on the right', () => {
  assert.deepEqual(podiumLeaders([1, 2, 3, 4, 5]), [3, 1, 2]);
  assert.deepEqual(podiumLeaders([1, 2]), [1, 2]);
});

test('equal totals share competition places throughout the list', () => {
  const leaders = [44, 36, 18, 18, 12].map(value => ({value}));
  assert.deepEqual(rankLeaders(leaders, 'points').map(row => row.rank), [1, 2, 3, 3, 5]);
});

test('equal exact pass ratios share first place despite different attempts', () => {
  const leaders = [[3, 6], [2, 4], [1, 2], [1, 3]].map(([passes_completed, passes_attempted]) => ({
    value: Math.round(passes_completed / passes_attempted * 100), passes_completed, passes_attempted,
  }));
  assert.deepEqual(rankLeaders(leaders, 'completion_percentage').map(row => row.rank), [1, 1, 1, 4]);
});

test('rounding a percentage does not manufacture a tie', () => {
  const leaders = [[4999, 10000], [4998, 10000]].map(([passes_completed, passes_attempted]) => ({
    value: 50, passes_completed, passes_attempted,
  }));
  assert.deepEqual(rankLeaders(leaders, 'completion_percentage').map(row => row.rank), [1, 2]);
});
