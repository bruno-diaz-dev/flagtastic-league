export type MobileMode = 'player' | 'referee' | 'representative';

export const modeLabels: Record<MobileMode, string> = {
  player: 'jugador', referee: 'árbitro', representative: 'representante',
};

export function availableModes(roles: string[]): MobileMode[] {
  const modes: MobileMode[] = [];
  if (roles.includes('referee')) modes.push('referee');
  if (roles.includes('team_representative')) modes.push('representative');
  if (roles.includes('player')) modes.push('player');
  return modes;
}

export function defaultMode(roles: string[]): MobileMode | null {
  return availableModes(roles)[0] ?? null;
}

export function visibleTabs(mode: MobileMode): string[] {
  if (mode === 'referee') return ['index', 'assignments', 'history', 'profile'];
  if (mode === 'representative') return ['index', 'teams', 'team-games', 'standings', 'profile'];
  return ['index', 'standings', 'leaders', 'stats', 'profile'];
}
