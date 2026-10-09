import { StyleSheet, Text, View } from 'react-native';

import { Avatar, Metric, TeamLogo, WebLink } from '@/components/LeagueUI';
import { EmptyState, Panel, Pill, Screen, SectionTitle } from '@/components/Screen';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import { colors, font } from '@/theme';
import { useAuth } from '@/providers/AuthProvider';
import { RefereeHome } from '@/components/RefereeScreens';

function formatTime(value: string | null) {
  if (!value) return 'Por confirmar';
  return value.slice(0, 5);
}

export default function HomeScreen() {
  const {mode} = useAuth();
  return mode === 'referee' ? <RefereeHome /> : <PlayerHome />;
}

function PlayerHome() {
  const {dashboard, games, loading, standings, activeTeam: team} = useLeagueData();
  if (loading && !dashboard) return <Screen title="Inicio"><EmptyState title="Cargando temporada" copy="Estamos preparando tu información." /></Screen>;
  if (!dashboard) return <Screen title="Inicio"><EmptyState title="Sin dashboard" copy="Tu cuenta todavía no tiene un perfil de jugador vinculado." /></Screen>;

  const teamStanding = standings.find((row) => row.team_id === team?.team_id);
  const relevantGames = team ? games.filter((game) => game.home_team.id === team.team_id || game.away_team.id === team.team_id) : [];
  const nextGame = relevantGames
    .filter((game) => game.status !== 'completed' && game.status !== 'postponed')
    .sort((a, b) => a.week - b.week || String(a.start_time).localeCompare(String(b.start_time)))[0];
  const latestGame = relevantGames
    .filter((game) => game.status === 'completed')
    .sort((a, b) => b.week - a.week || b.id - a.id)[0];
  const stats = dashboard.statistics;

  return (
    <Screen title="Inicio">
      <View style={styles.profileRow}>
        <Avatar name={dashboard.player.name} url={dashboard.player.profile_photo_url} size={62} />
        <View style={styles.grow}>
          <Text style={styles.welcome}>HOLA, {(dashboard.player.aka || dashboard.player.name.split(' ')[0]).toUpperCase()}</Text>
          <Text style={styles.subtitle}>Tu temporada, en un solo lugar.</Text>
        </View>
        {team ? <Pill>{team.category.toUpperCase()}</Pill> : null}
      </View>

      {team ? (
        <Panel style={styles.teamCard}>
          <View style={styles.teamTop}>
            <TeamLogo name={team.team_name} size={54} />
            <View style={styles.grow}>
              <Text style={styles.kicker}>MI EQUIPO</Text>
              <Text style={styles.teamName}>{team.team_name}</Text>
              <Text style={styles.meta}>{team.branch} · {team.category} · #{team.jersey_number}</Text>
            </View>
            <View style={styles.position}>
              <Text style={styles.positionValue}>{team.standing_position ?? '-'}</Text>
              <Text style={styles.positionLabel}>POSICIÓN</Text>
            </View>
          </View>
          <View style={styles.metrics}>
            <Metric label="Ganados" value={teamStanding?.wins ?? 0} accent />
            <Metric label="Perdidos" value={teamStanding?.losses ?? 0} />
            <Metric label="Diferencia" value={teamStanding ? `${teamStanding.point_difference > 0 ? '+' : ''}${teamStanding.point_difference}` : 0} />
          </View>
        </Panel>
      ) : <EmptyState title="Aún no tienes equipo" copy="Únete a un roster desde tu perfil en la versión web." />}

      <SectionTitle icon="calendar-outline">Próximo partido</SectionTitle>
      {nextGame ? (
        <Panel style={styles.gameCard}>
          <View style={styles.gameMeta}><Pill tone="orange">JORNADA {nextGame.week}</Pill><Text style={styles.gameMetaText}>{formatTime(nextGame.start_time)} · Campo {nextGame.field_number ?? '-'}</Text></View>
          <View style={styles.matchup}>
            <View style={styles.teamSide}><TeamLogo name={nextGame.home_team.name} url={nextGame.home_team.logo_url} size={48} /><Text style={styles.matchTeam}>{nextGame.home_team.name}</Text></View>
            <Text style={styles.vs}>VS</Text>
            <View style={styles.teamSide}><TeamLogo name={nextGame.away_team.name} url={nextGame.away_team.logo_url} size={48} /><Text style={styles.matchTeam}>{nextGame.away_team.name}</Text></View>
          </View>
          <WebLink path={`/games/${nextGame.id}`} label="Ver detalles del partido" icon="american-football-outline" />
        </Panel>
      ) : <EmptyState title="Sin partido próximo" copy="Tu siguiente juego aparecerá aquí cuando se publique el rol." />}

      <SectionTitle icon="flash-outline">Mi temporada</SectionTitle>
      <View style={styles.metrics}>
        <Metric label="Puntos" value={stats.points} accent />
        <Metric label="Recepciones" value={stats.receptions} />
        <Metric label="Tacleos" value={stats.tackles} />
        <Metric label="Pases %" value={stats.completion_percentage == null ? '-' : `${stats.completion_percentage}%`} />
      </View>

      {latestGame ? <WebLink path={`/games/${latestGame.id}`} label={`Último resultado: ${latestGame.home_team.name} ${latestGame.home_score} - ${latestGame.away_score} ${latestGame.away_team.name}`} /> : null}
      <WebLink path="/games" label="Ver calendario completo" icon="calendar-outline" />
      <WebLink path="/dashboard" label="Administrar mi perfil" icon="person-outline" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  profileRow: {flexDirection: 'row', alignItems: 'center', gap: 12},
  grow: {flex: 1},
  welcome: {fontFamily: font.displayBold, color: colors.white, fontSize: 20},
  subtitle: {fontFamily: font.body, color: colors.muted, fontSize: 13, marginTop: 3},
  teamCard: {gap: 16},
  teamTop: {flexDirection: 'row', alignItems: 'center', gap: 12},
  kicker: {fontFamily: font.displayBold, fontSize: 10, letterSpacing: 1, color: colors.gold},
  teamName: {fontFamily: font.displayBold, color: colors.white, fontSize: 20},
  meta: {fontFamily: font.body, color: colors.muted, fontSize: 12, marginTop: 2, textTransform: 'capitalize'},
  position: {alignItems: 'center'},
  positionValue: {fontFamily: font.displayBold, color: colors.gold, fontSize: 29},
  positionLabel: {fontFamily: font.bodyMedium, color: colors.muted, fontSize: 8},
  metrics: {flexDirection: 'row', gap: 8},
  gameCard: {gap: 14},
  gameMeta: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  gameMetaText: {fontFamily: font.bodyMedium, color: colors.text, fontSize: 12},
  matchup: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around'},
  teamSide: {flex: 1, alignItems: 'center', gap: 7},
  matchTeam: {fontFamily: font.displayBold, color: colors.white, fontSize: 14, textAlign: 'center'},
  vs: {fontFamily: font.displayBold, color: colors.orange, fontSize: 13, paddingHorizontal: 8},
});
