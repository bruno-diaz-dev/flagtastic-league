import {useState} from 'react';
import {useRouter} from 'expo-router';
import {Pressable, StyleSheet, Text, View} from 'react-native';

import {Avatar, Metric, TeamLogo, WebLink} from '@/components/LeagueUI';
import {EmptyState, Panel, Pill, Screen, SectionTitle} from '@/components/Screen';
import {chronological, gameState} from '@/lib/referee';
import {useAuth} from '@/providers/AuthProvider';
import {useLeagueData} from '@/providers/LeagueDataProvider';
import {colors, font} from '@/theme';
import type {Game, ManagedTeam} from '@/types';

function Action({label, onPress}: {label: string; onPress: () => void}) {
  return <Pressable accessibilityRole="button" style={styles.action} onPress={onPress}>
    <Text style={styles.actionText}>{label} →</Text>
  </Pressable>;
}

function TeamHeading({team}: {team: ManagedTeam}) {
  return <View style={styles.row}>
    <TeamLogo name={team.name} url={team.logo_url} size={52} />
    <View style={styles.grow}>
      <Text style={styles.name}>{team.name}</Text>
      <Text style={styles.meta}>{team.branch} · {team.category.toUpperCase()}</Text>
    </View>
    <Pill>#{team.standing.position ?? '—'}</Pill>
  </View>;
}

function GameCard({game}: {game: Game}) {
  const state = gameState(game);
  return <Panel style={styles.card}>
    <View style={styles.row}><Pill>JORNADA {game.week}</Pill><Text style={styles.meta}>
      {game.start_time?.slice(0, 5) || 'Por confirmar'} · Campo {game.field_number ?? '—'}
    </Text></View>
    <View style={styles.row}>
      <TeamLogo name={game.home_team.name} url={game.home_team.logo_url} size={34} />
      <Text style={[styles.body, styles.grow]}>{game.home_team.name} vs {game.away_team.name}</Text>
      <TeamLogo name={game.away_team.name} url={game.away_team.logo_url} size={34} />
    </View>
    <Text style={styles.name}>{state === 'postponed' ? 'Pospuesto' : state === 'completed'
      ? `${game.home_score ?? '—'} – ${game.away_score ?? '—'}` : 'Por jugar'}</Text>
    <WebLink path={`/games/${game.id}`} label="Ver detalles del partido" />
  </Panel>;
}

function LoadingOrEmpty({loading}: {loading: boolean}) {
  return <EmptyState title={loading ? 'Cargando tus equipos' : 'Sin equipos asignados'}
    copy={loading ? 'Estamos preparando tu información.' : 'La liga debe asignarte como representante de un equipo para que aparezca aquí.'} />;
}

export function RepresentativeHome() {
  const {user} = useAuth();
  const {representativeDashboard, activeManagedTeam: team, games, loading, selectTeam} = useLeagueData();
  const router = useRouter();
  const teams = representativeDashboard?.teams || [];
  const nextGame = team ? games.filter(game => (game.home_team.id === team.id || game.away_team.id === team.id)
    && gameState(game) === 'pending').sort(chronological)[0] : undefined;
  return <Screen title="Mis equipos">
    <Text style={styles.name}>Hola, {user?.display_name || user?.name}</Text>
    <Pill>REPRESENTANTE</Pill>
    <Text style={styles.body}>Consulta tus equipos, planteles y próximos partidos.</Text>
    {!teams.length ? <LoadingOrEmpty loading={loading} /> : <>
      <View style={styles.row}>
        <Metric label="Equipos" value={teams.length} accent />
        <Metric label="Jugadores" value={teams.reduce((total, item) => total + item.roster_count, 0)} />
      </View>
      {teams.map(item => <Panel key={item.id} style={styles.card}>
        <TeamHeading team={item} />
        <View style={styles.row}>
          <Metric label="Ganados" value={item.standing.wins} accent />
          <Metric label="Perdidos" value={item.standing.losses} />
          <Metric label="Plantel" value={item.roster_count} />
        </View>
        <Action label="Ver plantel y estadísticas" onPress={() => {void selectTeam(item.id); router.push('/teams');}} />
      </Panel>)}
      <SectionTitle icon="calendar-outline">Próximo partido{team ? ` · ${team.name}` : ''}</SectionTitle>
      {nextGame ? <GameCard game={nextGame} /> : <EmptyState title="Sin partidos pendientes" copy="Las próximas jornadas aparecerán cuando la liga publique el rol." />}
      <Action label="Consultar líderes de la división" onPress={() => router.push('/leaders')} />
    </>}
    <WebLink path="/representative-dashboard" label="Administrar equipos en la web" />
  </Screen>;
}

export function RepresentativeTeams() {
  const {activeManagedTeam: team, loading} = useLeagueData();
  return <Screen title="Plantel y estadísticas">
    {!team ? <LoadingOrEmpty loading={loading} /> : <>
      <Panel style={styles.card}>
        <TeamHeading team={team} />
        <Text style={styles.meta}>{team.roster_count} jugadores activos</Text>
        {team.head_coach ? <Text style={styles.body}>Head Coach: {team.head_coach}</Text> : null}
        {team.coach ? <Text style={styles.body}>Coach: {team.coach}</Text> : null}
        {team.manager ? <Text style={styles.body}>Manager: {team.manager}</Text> : null}
      </Panel>
      <SectionTitle icon="stats-chart-outline">Temporada del equipo</SectionTitle>
      <View style={styles.row}>
        <Metric label="Puntos" value={team.statistics.points} accent />
        <Metric label="Recepciones" value={team.statistics.receptions} />
        <Metric label="Tacleos" value={team.statistics.tackles} />
      </View>
      <View style={styles.row}>
        <Metric label="Intercepciones" value={team.statistics.interceptions} />
        <Metric label="Capturas" value={team.statistics.sacks} />
        <Metric label="Pases %" value={team.statistics.completion_percentage == null ? '—' : `${team.statistics.completion_percentage}%`} />
      </View>
      <SectionTitle icon="people-outline">Plantel activo</SectionTitle>
      {!team.players.length ? <EmptyState title="Plantel vacío" copy="Agrega jugadores desde la administración del equipo en la web." /> : team.players.map(player => <Panel key={player.player_id} style={styles.card}>
        <View style={styles.row}>
          <Avatar name={player.player_name} size={40} />
          <View style={styles.grow}>
            <Text style={styles.body}>{player.player_aka || player.player_name}</Text>
            {player.player_aka ? <Text style={styles.meta}>{player.player_name}</Text> : null}
          </View>
          <Pill>#{player.jersey_number}</Pill>
        </View>
        <Text style={styles.meta}>{player.points} puntos · {player.receptions} recepciones · {player.tackles} tacleos</Text>
        <Text style={styles.meta}>{player.interceptions} intercepciones · {player.sacks} capturas · Pases: {player.passes_completed}/{player.passes_attempted}</Text>
        <WebLink path={`/players/${player.player_id}`} label="Consultar perfil del jugador" />
      </Panel>)}
      <WebLink path={`/teams/${team.id}/manage`} label="Administrar plantel en la web" />
    </>}
  </Screen>;
}

export function RepresentativeGames() {
  const {games, activeManagedTeam: team, loading, representativeDashboard} = useLeagueData();
  const [filter, setFilter] = useState<'pending' | 'completed' | 'postponed'>('pending');
  const [allTeams, setAllTeams] = useState(false);
  const filtered = games.filter(game => gameState(game) === filter
    && (allTeams || game.home_team.id === team?.id || game.away_team.id === team?.id)).sort(chronological);
  return <Screen title="Partidos de mis equipos">
    {!representativeDashboard?.teams.length ? <LoadingOrEmpty loading={loading} /> : <>
      <Action label={allTeams ? 'Ver equipo seleccionado' : 'Ver todos mis equipos'} onPress={() => setAllTeams(!allTeams)} />
      <Text style={styles.meta}>{allTeams ? 'Todos mis equipos' : team?.name}</Text>
      <View style={styles.row}>
        {(['pending', 'completed', 'postponed'] as const).map(value => <Pressable key={value} accessibilityRole="button"
          accessibilityState={{selected: value === filter}} onPress={() => setFilter(value)} style={[styles.filter, value === filter && styles.selected]}>
          <Text style={styles.body}>{value === 'pending' ? 'Próximos' : value === 'completed' ? 'Resultados' : 'Pospuestos'}</Text>
        </Pressable>)}
      </View>
      {filtered.length ? filtered.map(game => <GameCard key={game.id} game={game} />)
        : <EmptyState title="Sin partidos en esta vista" copy="Consulta otra vista o desliza hacia abajo para actualizar." />}
    </>}
  </Screen>;
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 8},
  grow: {flex: 1},
  card: {gap: 12},
  name: {fontFamily: font.displayBold, fontSize: 20, color: colors.white},
  body: {fontFamily: font.bodyMedium, fontSize: 13, color: colors.text},
  meta: {fontFamily: font.body, fontSize: 11, color: colors.muted, lineHeight: 17},
  action: {padding: 16, backgroundColor: colors.cardHigh, borderRadius: 10},
  actionText: {fontFamily: font.display, color: colors.gold, fontSize: 14},
  filter: {flex: 1, paddingVertical: 12, alignItems: 'center', borderWidth: 1, borderColor: colors.border, borderRadius: 8},
  selected: {backgroundColor: colors.cardHigh, borderColor: colors.gold},
});
