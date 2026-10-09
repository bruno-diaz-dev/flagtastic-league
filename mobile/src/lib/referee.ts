import type { Game } from '../types';

export const positions: Record<string, string> = {
  referee: 'Referee', down_judge: 'Down Judge', field_judge: 'Field Judge',
  side_judge: 'Side Judge', statistician: 'Estadístico',
};

export function gameState(game: Pick<Game, 'status' | 'home_score' | 'away_score'>) {
  if (game.status === 'postponed') return 'postponed';
  if (game.status === 'completed' || (game.home_score != null && game.away_score != null)) return 'completed';
  return 'pending';
}

export function chronological(a: Pick<Game, 'id' | 'week' | 'start_time'>, b: Pick<Game, 'id' | 'week' | 'start_time'>) {
  return a.week - b.week || (a.start_time || '99:99').localeCompare(b.start_time || '99:99') || a.id - b.id;
}
