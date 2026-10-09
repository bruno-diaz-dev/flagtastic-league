import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { loadDashboard, loadGames, loadLeaderboards, loadStandings, loadRefereeGames, loadRefereeProfile } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import type { Game, Leaderboards, PlayerDashboard, RefereeGame, RefereeProfile, Standing } from '@/types';

type LeagueDataValue = {
  refereeGames: RefereeGame[];
  refereeProfile: RefereeProfile | null;
  dashboard: PlayerDashboard | null;
  games: Game[];
  standings: Standing[];
  leaderboards: Leaderboards;
  loading: boolean;
  refreshing: boolean;
  error: string;
  refresh: () => Promise<void>;
};

const LeagueDataContext = createContext<LeagueDataValue | null>(null);

export function LeagueDataProvider({ children }: PropsWithChildren) {
  const { token, mode } = useAuth();
  const [refereeGames, setRefereeGames] = useState<RefereeGame[]>([]);
  const [refereeProfile, setRefereeProfile] = useState<RefereeProfile | null>(null);
  const requestId = useRef(0);
  const [dashboard, setDashboard] = useState<PlayerDashboard | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [leaderboards, setLeaderboards] = useState<Leaderboards>({});
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    if (!token) return;
    const id = ++requestId.current;
    setRefreshing(true);
    setError('');
    try {
      if (mode === 'referee') {
        const [assignments, profile] = await Promise.all([loadRefereeGames(token), loadRefereeProfile(token)]);
        if (id !== requestId.current) return;
        setRefereeGames(assignments);
        setRefereeProfile(profile);
        return;
      }
      const [nextDashboard, nextGames] = await Promise.all([
        loadDashboard(token),
        loadGames(token),
      ]);
      if (id !== requestId.current) return;
      setDashboard(nextDashboard);
      setGames(nextGames);
      const team = nextDashboard.teams[0];
      if (team) {
        const [nextStandings, nextLeaderboards] = await Promise.all([
          loadStandings(team.branch, team.category),
          loadLeaderboards(team.branch, team.category),
        ]);
        if (id !== requestId.current) return;
        setStandings(nextStandings);
        setLeaderboards(nextLeaderboards);
      } else {
        setStandings([]);
        setLeaderboards({});
      }
    } catch (caught) {
      if (id !== requestId.current) return;
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los datos.');
    } finally {
      if (id === requestId.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [token, mode]);

  useEffect(() => {
    setDashboard(null);
    setRefereeGames([]);
    setRefereeProfile(null);
    setGames([]);
    setStandings([]);
    setLeaderboards({});
    if (!token) {
      setDashboard(null);
      return;
    }
    setLoading(true);
    void refresh();
    return () => { requestId.current += 1; };
  }, [token, refresh]);

  const value = useMemo(
    () => ({dashboard, games, standings, leaderboards, refereeGames, refereeProfile, loading, refreshing, error, refresh}),
    [dashboard, games, standings, leaderboards, refereeGames, refereeProfile, loading, refreshing, error, refresh],
  );
  return <LeagueDataContext.Provider value={value}>{children}</LeagueDataContext.Provider>;
}

export function useLeagueData() {
  const value = useContext(LeagueDataContext);
  if (!value) throw new Error('useLeagueData must be used inside LeagueDataProvider');
  return value;
}

