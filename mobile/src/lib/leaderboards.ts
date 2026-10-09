import type { Leader } from '../types';

// Older API responses have no rank. Compare the exact pass ratio rather than
// rounded percentages, and use competition ranks (1, 1, 3).
export function rankLeaders(leaders: Leader[], metric: string): (Leader & {rank: number})[] {
  let rank = 0;
  return leaders.map((leader, index) => {
    const previous = leaders[index - 1];
    const hasPasses = metric === 'completion_percentage'
      && leader.passes_attempted && previous?.passes_attempted
      && leader.passes_completed != null && previous.passes_completed != null;
    const tied = previous && (hasPasses
      ? leader.passes_completed! * previous.passes_attempted! === previous.passes_completed! * leader.passes_attempted!
      : leader.value === previous.value);
    if (!tied) rank = index + 1;
    return {...leader, rank: leader.rank ?? rank};
  });
}

export function podiumLeaders<T>(leaders: T[]): T[] {
  const top = leaders.slice(0, 3);
  return top.length >= 2 ? [top[1], top[0], ...top.slice(2)] : top;
}
