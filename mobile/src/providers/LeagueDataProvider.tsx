import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError, loadDashboard, loadGames, loadLeaderboards, loadStandings } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import type { Game, Leaderboards, PlayerDashboard, Standing, TeamSummary } from '@/types';

type LeagueDataValue = {
  dashboard: PlayerDashboard | null;
  games: Game[];
  standings: Standing[];
  leaderboards: Leaderboards;
  activeTeam: TeamSummary | null;
  loading: boolean;
  refreshing: boolean;
  error: string;
  refresh: () => Promise<void>;
  selectTeam: (teamId: number) => Promise<void>;
};

const LeagueDataContext = createContext<LeagueDataValue | null>(null);

export function LeagueDataProvider({ children }: PropsWithChildren) {
  const { token, signOut } = useAuth();
  const [dashboard, setDashboard] = useState<PlayerDashboard | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [leaderboards, setLeaderboards] = useState<Leaderboards>({});
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [activeTeamId, setActiveTeamId] = useState<number | null>(null);
  const activeTeamIdRef = useRef<number | null>(null);

  const loadDivision = useCallback(async (team?: TeamSummary) => {
    if (!team) {
      setStandings([]);
      setLeaderboards({});
      return;
    }
    const [nextStandings, nextLeaderboards] = await Promise.all([
      loadStandings(team.branch, team.category),
      loadLeaderboards(team.branch, team.category),
    ]);
    setStandings(nextStandings);
    setLeaderboards(nextLeaderboards);
  }, []);

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
      const team = nextDashboard.teams.find(({team_id}) => team_id === activeTeamIdRef.current)
        || nextDashboard.teams[0];
      activeTeamIdRef.current = team?.team_id ?? null;
      setActiveTeamId(team?.team_id ?? null);
      await loadDivision(team);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        await signOut();
        return;
      }
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los datos.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, loadDivision, signOut]);

  const selectTeam = useCallback(async (teamId: number) => {
    const team = dashboard?.teams.find(({team_id}) => team_id === teamId);
    if (!team || teamId === activeTeamId) return;
    activeTeamIdRef.current = teamId;
    setActiveTeamId(teamId);
    setRefreshing(true);
    setError('');
    try {
      await loadDivision(team);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo cambiar de división.');
    } finally {
      setRefreshing(false);
    }
  }, [activeTeamId, dashboard, loadDivision]);

  useEffect(() => {
    if (!token) {
      setDashboard(null);
      activeTeamIdRef.current = null;
      setActiveTeamId(null);
      return;
    }
    setLoading(true);
    void refresh();
  }, [token, refresh]);

  const activeTeam = dashboard?.teams.find(({team_id}) => team_id === activeTeamId)
    || dashboard?.teams[0]
    || null;
  const value = useMemo(
    () => ({dashboard, games, standings, leaderboards, activeTeam, loading, refreshing, error, refresh, selectTeam}),
    [dashboard, games, standings, leaderboards, activeTeam, loading, refreshing, error, refresh, selectTeam],
  );
  return <LeagueDataContext.Provider value={value}>{children}</LeagueDataContext.Provider>;
}

export function useLeagueData() {
  const value = useContext(LeagueDataContext);
  if (!value) throw new Error('useLeagueData must be used inside LeagueDataProvider');
  return value;
}
