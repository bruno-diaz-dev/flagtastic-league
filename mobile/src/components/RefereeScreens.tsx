import { useState } from 'react';
import { Redirect, useRouter } from 'expo-router';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { Avatar, Metric, TeamLogo, WebLink } from '@/components/LeagueUI';
import { EmptyState, Panel, Pill, Screen, SectionTitle } from '@/components/Screen';
import { chronological, gameState, positions } from '@/lib/referee';
import { useAuth } from '@/providers/AuthProvider';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import { colors, font } from '@/theme';
import type { RefereeGame } from '@/types';

function GameCard({game}: {game: RefereeGame}) {
  const [expanded, setExpanded] = useState(false);
  const {user} = useAuth();
  const state = gameState(game);
  return <Panel style={{gap: 14}}>
    <View style={styles.row}><Pill tone={state === 'postponed' ? 'orange' : 'gold'}>{state === 'completed' ? 'FINALIZADO' : state === 'postponed' ? 'POSPUESTO' : 'POR ARBITRAR'}</Pill><Text style={styles.meta}>Jornada {game.week}</Text></View>
    <View style={styles.matchup}>
      <TeamLogo name={game.home_team.name} url={game.home_team.logo_url} size={36} />
      <View style={{flex: 1}}><Text style={styles.title}>{game.home_team.name}</Text><Text style={styles.meta}>vs</Text><Text style={styles.title}>{game.away_team.name}</Text></View>
      <TeamLogo name={game.away_team.name} url={game.away_team.logo_url} size={36} />
    </View>
    <Text style={styles.accent}>Tu puesto: {positions[game.official_position] || game.official_position}</Text>
    <Text style={styles.meta}>{game.home_team.branch} · {game.home_team.category}{game.is_friendly ? ' · Amistoso' : ''}</Text>
    <Text style={styles.copy}>{game.start_time?.slice(0, 5) || 'Hora por confirmar'} · {game.field_number == null ? 'Campo por confirmar' : `Campo ${game.field_number}`}</Text>
    {state === 'postponed' ? <Text style={styles.meta}>Espera la confirmación de un nuevo horario.</Text> : null}
    {state === 'completed' ? <Text style={styles.score}>{game.home_score ?? '—'} – {game.away_score ?? '—'}</Text> : null}
    <Pressable accessibilityRole="button" accessibilityState={{expanded}} onPress={() => setExpanded(!expanded)} style={styles.button}>
      <Text style={styles.accent}>{expanded ? 'Ocultar' : 'Ver'} planilla arbitral</Text>
    </Pressable>
    {expanded ? <View style={{gap: 12}}>
      {game.officials.length ? game.officials.map(official => <View key={official.user_id} style={styles.matchup}>
        <Avatar name={official.display_name} url={official.profile_photo_url} size={36} />
        <View style={{flex: 1}}><Text style={styles.copy}>{official.display_name}{official.user_id === user?.id ? ' (Tú)' : ''}</Text><Text style={styles.meta}>{positions[official.position] || official.position}</Text></View>
      </View>) : <Text style={styles.meta}>Sin compañeros asignados todavía.</Text>}
    </View> : null}
    <WebLink path={`/games/${game.id}`} label="Detalle completo en la web" />
  </Panel>;
}

function LoadState() {
  const {loading, error, refresh} = useLeagueData();
  if (loading) return <ActivityIndicator accessibilityLabel="Cargando asignaciones" size="large" color={colors.gold} />;
  if (error) return <Pressable accessibilityRole="button" style={styles.button} onPress={() => void refresh()}><Text style={styles.accent}>Reintentar carga</Text></Pressable>;
  return null;
}

export function RefereeHome() {
  const {user} = useAuth();
  const {refereeGames: games, refereeProfile, loading, error} = useLeagueData();
  const router = useRouter();
  const pending = games.filter(game => gameState(game) === 'pending').sort(chronological);
  const completed = games.filter(game => gameState(game) === 'completed');
  const postponed = games.filter(game => gameState(game) === 'postponed');
  return <Screen title="Mi arbitraje">
    <View style={styles.matchup}>
      <Avatar name={user?.name || ''} url={refereeProfile?.profile_photo_url} size={60} />
      <View style={{flex: 1}}><Text style={styles.heading}>Hola, {refereeProfile?.display_name || user?.display_name || user?.name}</Text><Text style={styles.meta}>Tu jornada comienza aquí.</Text></View>
    </View>
    <Pill>ÁRBITRO</Pill>
    <LoadState />
    {!loading && (!error || games.length > 0) ? <>
      <View style={styles.matchup}><Metric label="Por arbitrar" value={pending.length} accent /><Metric label="Pospuestos" value={postponed.length} /><Metric label="Finalizados" value={completed.length} /></View>
      <SectionTitle icon="calendar-outline">Próxima asignación</SectionTitle>
      {pending[0] ? <GameCard key={pending[0].id} game={pending[0]} /> : <EmptyState title="Sin partidos pendientes" copy="Tus próximas asignaciones aparecerán cuando la liga publique la planilla." />}
      {postponed.length > 0 ? <Text style={styles.copy}>Tienes {postponed.length} partido(s) pendiente(s) de reprogramación. Consúltalos en tu agenda.</Text> : null}
      <Pressable accessibilityRole="button" style={styles.button} onPress={() => router.push('/assignments')}><Text style={styles.accent}>Ver toda mi agenda →</Text></Pressable>
      <Pressable accessibilityRole="button" style={styles.button} onPress={() => router.push('/history')}><Text style={styles.accent}>Consultar mi historial →</Text></Pressable>
    </> : null}
  </Screen>;
}

export function RefereeAgenda() {
  const {mode} = useAuth();
  const {refereeGames, loading, error} = useLeagueData();
  const [filter, setFilter] = useState<'pending' | 'postponed'>('pending');
  if (mode !== 'referee') return <Redirect href="/" />;
  const games = refereeGames.filter(game => gameState(game) === filter).sort(chronological);
  return <Screen title="Mi agenda">
    <Text style={styles.copy}>Consulta tus horarios, campos y puestos antes de cada jornada.</Text>
    <View style={styles.matchup}>{(['pending', 'postponed'] as const).map(value => <Pressable key={value} accessibilityRole="button" accessibilityState={{selected: filter === value}} onPress={() => setFilter(value)} style={[styles.button, {flex: 1}, filter === value && styles.selected]}><Text style={styles.accent}>{value === 'pending' ? 'Pendientes' : 'Pospuestos'}</Text></Pressable>)}</View>
    <LoadState />
    {!loading && !error && !games.length ? <EmptyState title={filter === 'pending' ? 'Sin asignaciones pendientes' : 'Sin partidos pospuestos'} copy="Desliza hacia abajo para consultar actualizaciones de la liga." /> : null}
    {games.map(game => <GameCard key={game.id} game={game} />)}
  </Screen>;
}

export function RefereeHistory() {
  const {mode} = useAuth();
  const {refereeGames, loading, error} = useLeagueData();
  if (mode !== 'referee') return <Redirect href="/" />;
  const games = refereeGames.filter(game => gameState(game) === 'completed').sort((a, b) => chronological(b, a));
  const weeks = [...new Set(games.map(game => game.week))];
  return <Screen title="Mi historial">
    <Text style={styles.copy}>Tu experiencia en la liga, partido a partido.</Text>
    <LoadState />
    {!loading && (!error || games.length > 0) ? <>
      <View style={styles.matchup}><Metric label="Arbitrajes" value={games.length} accent /><Metric label="Jornadas" value={weeks.length} /></View>
      {games.length ? <Panel style={{gap: 12}}><Text style={styles.title}>Participación por puesto</Text>{Object.entries(positions).map(([position, label]) => {
        const count = games.filter(game => game.official_position === position).length;
        return count ? <View key={position} style={styles.row}><Text style={styles.copy}>{label}</Text><Text style={styles.accent}>{count}</Text></View> : null;
      })}</Panel> : <EmptyState title="Tu historial está por comenzar" copy="Aquí aparecerán los resultados de tus partidos finalizados." />}
    </> : null}
    {weeks.map(week => <View key={week} style={{gap: 14}}><SectionTitle>Jornada {week}</SectionTitle>{games.filter(game => game.week === week).map(game => <GameCard key={game.id} game={game} />)}</View>)}
  </Screen>;
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap'},
  matchup: {flexDirection: 'row', alignItems: 'center', gap: 10},
  heading: {fontFamily: font.displayBold, fontSize: 23, color: colors.white},
  title: {fontFamily: font.displayBold, fontSize: 17, color: colors.white},
  meta: {fontFamily: font.body, fontSize: 12, color: colors.muted},
  copy: {fontFamily: font.body, fontSize: 14, color: colors.text, lineHeight: 21},
  accent: {fontFamily: font.display, color: colors.gold, fontSize: 14},
  score: {fontFamily: font.displayBold, fontSize: 28, color: colors.white},
  button: {padding: 15, minHeight: 48, borderRadius: 8, backgroundColor: colors.cardHigh},
  selected: {borderWidth: 1, borderColor: colors.gold},
});
