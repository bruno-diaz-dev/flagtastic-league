import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { loadDashboard, loadGames, loadLeaderboards, loadStandings } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import type { Game, Leaderboards, PlayerDashboard, Standing } from '@/types';

type LeagueDataValue = {
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
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<PlayerDashboard | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [leaderboards, setLeaderboards] = useState<Leaderboards>({});
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    if (!token) return;
    setRefreshing(true);
    setError('');
    try {
      const [nextDashboard, nextGames] = await Promise.all([
        loadDashboard(token),
        loadGames(token),
      ]);
      setDashboard(nextDashboard);
      setGames(nextGames);
      const team = nextDashboard.teams[0];
      if (team) {
        const [nextStandings, nextLeaderboards] = await Promise.all([
          loadStandings(team.branch, team.category),
          loadLeaderboards(team.branch, team.category),
        ]);
        setStandings(nextStandings);
        setLeaderboards(nextLeaderboards);
      } else {
        setStandings([]);
        setLeaderboards({});
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los datos.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      setDashboard(null);
      return;
    }
    setLoading(true);
    void refresh();
  }, [token, refresh]);

  const value = useMemo(
    () => ({dashboard, games, standings, leaderboards, loading, refreshing, error, refresh}),
    [dashboard, games, standings, leaderboards, loading, refreshing, error, refresh],
  );
  return <LeagueDataContext.Provider value={value}>{children}</LeagueDataContext.Provider>;
}

export function useLeagueData() {
  const value = useContext(LeagueDataContext);
  if (!value) throw new Error('useLeagueData must be used inside LeagueDataProvider');
  return value;
}

