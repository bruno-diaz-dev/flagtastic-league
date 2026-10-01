import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar, Metric, TeamLogo, WebLink } from '@/components/LeagueUI';
import { EmptyState, Panel, Pill, Screen } from '@/components/Screen';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import { colors, font } from '@/theme';

export default function StatsScreen() {
  const {dashboard} = useLeagueData();
  const [mode, setMode] = useState<'offense' | 'defense'>('offense');
  if (!dashboard) return <Screen title="Mis Stats"><EmptyState title="Sin estadísticas" copy="No encontramos un perfil de jugador vinculado." /></Screen>;
  const team = dashboard.teams[0];
  const stats = dashboard.statistics;

  return (
    <Screen title="Mis Stats">
      <Panel style={styles.identity}>
        <Avatar name={dashboard.player.name} url={dashboard.player.profile_photo_url} size={72} />
        <View style={styles.grow}>
          <Text style={styles.name}>{dashboard.player.aka || dashboard.player.name}</Text>
          <Text style={styles.legalName}>{dashboard.player.name}</Text>
          {team ? <View style={styles.teamLine}><TeamLogo name={team.team_name} size={24} /><Text style={styles.team}>{team.team_name} · #{team.jersey_number}</Text></View> : null}
        </View>
        <Pill>{stats.weeks} JORNADAS</Pill>
      </Panel>

      <View style={styles.segmented}>
        <Pressable onPress={() => setMode('offense')} style={[styles.segment, mode === 'offense' && styles.segmentActive]}><Text style={[styles.segmentText, mode === 'offense' && styles.segmentTextActive]}>OFENSIVA</Text></Pressable>
        <Pressable onPress={() => setMode('defense')} style={[styles.segment, mode === 'defense' && styles.segmentActive]}><Text style={[styles.segmentText, mode === 'defense' && styles.segmentTextActive]}>DEFENSIVA</Text></Pressable>
      </View>

      {mode === 'offense' ? (
        <>
          <Panel style={styles.efficiency}>
            <View><Text style={styles.kicker}>EFICIENCIA DE PASE</Text><Text style={styles.efficiencyValue}>{stats.completion_percentage == null ? '-' : `${stats.completion_percentage}%`}</Text></View>
            <View style={styles.passDetail}><Text style={styles.passValue}>{stats.passes_completed}/{stats.passes_attempted}</Text><Text style={styles.passLabel}>COMPLETOS / INTENTOS</Text></View>
          </Panel>
          <View style={styles.grid}><Metric label="Puntos" value={stats.points} accent /><Metric label="Recepciones" value={stats.receptions} /><Metric label="Pases completos" value={stats.passes_completed} /></View>
        </>
      ) : (
        <View style={styles.grid}><Metric label="Tacleos" value={stats.tackles} accent /><Metric label="Intercepciones" value={stats.interceptions} /><Metric label="Capturas" value={stats.sacks} /></View>
      )}

      <Panel>
        <Text style={styles.summaryTitle}>RESUMEN DE TEMPORADA</Text>
        <Text style={styles.summary}>Tus números acumulan las jornadas importadas oficialmente por la liga. Los detalles por partido están disponibles en la versión web.</Text>
      </Panel>
      <WebLink path="/dashboard" label="Abrir mi dashboard completo" icon="stats-chart-outline" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  identity: {flexDirection: 'row', alignItems: 'center', gap: 12},
  grow: {flex: 1},
  name: {fontFamily: font.displayBold, color: colors.white, fontSize: 21},
  legalName: {fontFamily: font.body, color: colors.muted, fontSize: 11, marginTop: 2},
  teamLine: {flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 7},
  team: {flex: 1, fontFamily: font.bodyMedium, color: colors.text, fontSize: 11},
  segmented: {flexDirection: 'row', padding: 4, borderRadius: 9, backgroundColor: colors.surface},
  segment: {flex: 1, alignItems: 'center', paddingVertical: 11, borderRadius: 7},
  segmentActive: {backgroundColor: colors.gold},
  segmentText: {fontFamily: font.displayBold, color: colors.muted, fontSize: 11, letterSpacing: 0.5},
  segmentTextActive: {color: colors.base},
  efficiency: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  kicker: {fontFamily: font.displayBold, color: colors.muted, fontSize: 10, letterSpacing: 0.8},
  efficiencyValue: {fontFamily: font.displayBold, color: colors.gold, fontSize: 42, marginTop: 2},
  passDetail: {alignItems: 'flex-end'},
  passValue: {fontFamily: font.displayBold, color: colors.white, fontSize: 22},
  passLabel: {fontFamily: font.bodyMedium, color: colors.muted, fontSize: 8, marginTop: 2},
  grid: {flexDirection: 'row', gap: 8},
  summaryTitle: {fontFamily: font.displayBold, color: colors.gold, fontSize: 11, letterSpacing: 0.8},
  summary: {fontFamily: font.body, color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 7},
});
