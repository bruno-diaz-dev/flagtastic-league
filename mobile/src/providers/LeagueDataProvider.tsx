import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError, loadDashboard, loadGames, loadLeaderboards, loadStandings, loadRefereeGames, loadRefereeProfile, loadRepresentativeDashboard } from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import type { Game, Leaderboards, PlayerDashboard, RefereeGame, RefereeProfile, RepresentativeDashboard, ManagedTeam, Standing, TeamSummary } from '@/types';

type LeagueDataValue = {
  representativeDashboard: RepresentativeDashboard | null;
  activeManagedTeam: ManagedTeam | null;
  refereeGames: RefereeGame[];
  refereeProfile: RefereeProfile | null;
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
  const { token, mode, signOut } = useAuth();
  const [refereeGames, setRefereeGames] = useState<RefereeGame[]>([]);
  const [refereeProfile, setRefereeProfile] = useState<RefereeProfile | null>(null);
  const [representativeDashboard, setRepresentativeDashboard] = useState<RepresentativeDashboard | null>(null);
  const requestId = useRef(0);
  const [dashboard, setDashboard] = useState<PlayerDashboard | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [leaderboards, setLeaderboards] = useState<Leaderboards>({});
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [activeTeamId, setActiveTeamId] = useState<number | null>(null);
  const activeTeamIdRef = useRef<number | null>(null);

  const loadDivision = useCallback(async (team?: TeamSummary, id = requestId.current) => {
    if (!team) {
      setStandings([]);
      setLeaderboards({});
      return;
    }
    const [nextStandings, nextLeaderboards] = await Promise.all([
      loadStandings(team.branch, team.category),
      loadLeaderboards(team.branch, team.category),
    ]);
    if (id !== requestId.current) return;
    setStandings(nextStandings);
    setLeaderboards(nextLeaderboards);
  }, []);

  const refresh = useCallback(async () => {
    if (!token) return;
    const id = ++requestId.current;
    setRefreshing(true);
    setError('');
    try {
      if (mode === 'representative') {
        const [nextDashboard, nextGames] = await Promise.all([
          loadRepresentativeDashboard(token), loadGames(token),
        ]);
        if (id !== requestId.current) return;
        setRepresentativeDashboard(nextDashboard);
        const managed = nextDashboard.teams.find(team => team.id === activeTeamIdRef.current) || nextDashboard.teams[0];
        activeTeamIdRef.current = managed?.id ?? null;
        setActiveTeamId(managed?.id ?? null);
        const teamIds = new Set(nextDashboard.teams.map(team => team.id));
        setGames(nextGames.filter(game => teamIds.has(game.home_team.id) || teamIds.has(game.away_team.id)));
        await loadDivision(managed ? managedTeamSummary(managed) : undefined, id);
        return;
      }
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
      const team = nextDashboard.teams.find(({team_id}) => team_id === activeTeamIdRef.current)
        || nextDashboard.teams[0];
      activeTeamIdRef.current = team?.team_id ?? null;
      setActiveTeamId(team?.team_id ?? null);
      await loadDivision(team, id);
    } catch (caught) {
      if (id !== requestId.current) return;
      if (caught instanceof ApiError && caught.status === 401) {
        await signOut();
        return;
      }
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los datos.');
    } finally {
      if (id === requestId.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [token, mode, loadDivision, signOut]);

  const selectTeam = useCallback(async (teamId: number) => {
    const team = mode === 'representative'
      ? representativeDashboard?.teams.map(managedTeamSummary).find(({team_id}) => team_id === teamId)
      : dashboard?.teams.find(({team_id}) => team_id === teamId);
    if (!team || teamId === activeTeamId) return;
    const id = ++requestId.current;
    activeTeamIdRef.current = teamId;
    setActiveTeamId(teamId);
    setRefreshing(true);
    setError('');
    try {
      await loadDivision(team, id);
    } catch (caught) {
      if (id === requestId.current) setError(caught instanceof Error ? caught.message : 'No se pudo cambiar de división.');
    } finally {
      if (id === requestId.current) {setRefreshing(false); setLoading(false);}
    }
  }, [activeTeamId, dashboard, representativeDashboard, mode, loadDivision]);

  useEffect(() => {
    setDashboard(null);
    setRepresentativeDashboard(null);
    activeTeamIdRef.current = null;
    setActiveTeamId(null);
    setRefereeGames([]);
    setRefereeProfile(null);
    setGames([]);
    setStandings([]);
    setLeaderboards({});
    if (!token) {
      setDashboard(null);
      activeTeamIdRef.current = null;
      setActiveTeamId(null);
      return;
    }
    setLoading(true);
    void refresh();
    return () => { requestId.current += 1; };
  }, [token, refresh]);

  const activeManagedTeam = representativeDashboard?.teams.find(team => team.id === activeTeamId)
    || representativeDashboard?.teams[0] || null;
  const activeTeam = mode === 'representative' ? (activeManagedTeam ? managedTeamSummary(activeManagedTeam) : null) : dashboard?.teams.find(({team_id}) => team_id === activeTeamId)
    || dashboard?.teams[0]
    || null;
  const value = useMemo(
    () => ({representativeDashboard, activeManagedTeam, dashboard, games, standings, leaderboards, refereeGames, refereeProfile, activeTeam, loading, refreshing, error, refresh, selectTeam}),
    [representativeDashboard, activeManagedTeam, dashboard, games, standings, leaderboards, refereeGames, refereeProfile, activeTeam, loading, refreshing, error, refresh, selectTeam],
  );
  return <LeagueDataContext.Provider value={value}>{children}</LeagueDataContext.Provider>;
}

export function useLeagueData() {
  const value = useContext(LeagueDataContext);
  if (!value) throw new Error('useLeagueData must be used inside LeagueDataProvider');
  return value;
}

function managedTeamSummary(team: ManagedTeam): TeamSummary {
  return {team_id: team.id, team_name: team.name, branch: team.branch, category: team.category,
    standing_position: team.standing.position, division_team_count: team.standing.division_team_count};
}
