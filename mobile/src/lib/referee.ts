import type { RefereeGame } from '../types';

export const positions: Record<string, string> = {
  referee: 'Referee', down_judge: 'Down Judge', field_judge: 'Field Judge',
  side_judge: 'Side Judge', statistician: 'Estadístico',
};

export function gameState(game: RefereeGame) {
  if (game.status === 'postponed') return 'postponed';
  if (game.status === 'completed' || (game.home_score != null && game.away_score != null)) return 'completed';
  return 'pending';
}

export function chronological(a: RefereeGame, b: RefereeGame) {
  return a.week - b.week || (a.start_time || '99:99').localeCompare(b.start_time || '99:99') || a.id - b.id;
}
