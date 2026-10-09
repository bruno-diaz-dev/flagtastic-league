import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/components/LeagueUI';
import { EmptyState, Panel, Pill, Screen } from '@/components/Screen';
import { DivisionFilter } from '@/components/DivisionFilter';
import { useDivisionData } from '@/lib/useDivisionData';
import { podiumLeaders, rankLeaders } from '@/lib/leaderboards';
import { loadLeaderboards } from '@/lib/api';
import { colors, font } from '@/theme';

const metrics = [
  {key: 'points', label: 'Puntos', title: 'El Anotador', unit: 'PTS'},
  {key: 'receptions', label: 'Recepciones', title: 'Manos Seguras', unit: 'REC'},
  {key: 'tackles', label: 'Tacleos', title: 'El Muro', unit: 'TAC'},
  {key: 'interceptions', label: 'Intercepciones', title: 'Cazador Aéreo', unit: 'INT'},
  {key: 'sacks', label: 'Capturas', title: 'Cazador de QBs', unit: 'CAP'},
  {key: 'completion_percentage', label: 'Pases %', title: 'Francotirador', unit: '%'},
] as const;

export default function LeadersScreen() {
  const query = useDivisionData(loadLeaderboards);
  const {division, setDivision, team, data: leaderboards = {}, refreshing, error} = query;
  const [selected, setSelected] = useState<(typeof metrics)[number]['key']>('points');
  const metric = useMemo(() => metrics.find((item) => item.key === selected)!, [selected]);
  const leaders = rankLeaders(leaderboards[selected] || [], selected);

  return (
    <Screen title="Líderes" refreshControl={query}>
      <DivisionFilter division={division} onChange={setDivision} team={team} />
      <View style={styles.heading}><View><Text style={styles.kicker}>TOP 5 DE LA DIVISIÓN</Text><Text style={styles.title}>{metric.title}</Text></View><Pill>{division.branch.toUpperCase()} · {division.category.toUpperCase()}</Pill></View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabs}>
        {metrics.map((item) => <Pressable key={item.key} onPress={() => setSelected(item.key)} style={[styles.tab, selected === item.key && styles.tabActive]}><Text style={[styles.tabText, selected === item.key && styles.tabTextActive]}>{item.label}</Text></Pressable>)}
      </ScrollView>
      {refreshing ? <ActivityIndicator accessibilityLabel="Cargando estadísticas" color={colors.gold} /> : null}
      {leaders.length ? (
        <>
          <View style={styles.podium}>
            {podiumLeaders(leaders).map((leader) => (
              <View key={`${leader.player_id}-${leader.team_id}`} style={[styles.podiumItem, leader.rank === 1 && styles.first]}>
                <Text style={styles.place}>{leader.rank}</Text>
                <Avatar name={leader.player_name} url={leader.profile_photo_url} size={leader.rank === 1 ? 72 : 58} />
                <Text numberOfLines={1} style={styles.player}>{leader.player_aka || leader.player_name}</Text>
                <Text numberOfLines={1} style={styles.team}>{leader.team_name} · #{leader.jersey_number}</Text>
                <Text style={styles.score}>{leader.value}{metric.unit === '%' ? '%' : ''}</Text>
                <Text style={styles.unit}>{metric.unit}</Text>
                {selected === 'completion_percentage' && leader.passes_attempted != null ? <Text style={styles.team}>{leader.passes_completed}/{leader.passes_attempted} C/I</Text> : null}
              </View>
            ))}
          </View>
          <Panel style={styles.list}>
            {leaders.slice(3).map((leader) => (
              <View key={`${leader.player_id}-${leader.team_id}`} style={styles.listRow}>
                <Text style={styles.listPlace}>{leader.rank}</Text><Avatar name={leader.player_name} url={leader.profile_photo_url} size={40} />
                <View style={styles.listCopy}><Text style={styles.listName}>{leader.player_aka || leader.player_name}</Text><Text style={styles.listTeam}>{leader.team_name} · #{leader.jersey_number}</Text></View>
                <Text style={styles.listValue}>{leader.value}{metric.unit === '%' ? '%' : ''}</Text>
              </View>
            ))}
          </Panel>
          {selected === 'completion_percentage' && leaderboards.passing_qualification ? <Text style={styles.note}>Desde la jornada 4 se requieren {leaderboards.passing_qualification.minimum_attempts} pases lanzados para clasificar.</Text> : null}
        </>
      ) : !refreshing && !error ? <EmptyState title="Aún no hay líderes" copy="La clasificación aparecerá cuando se carguen estadísticas para esta división." /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  heading: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  kicker: {fontFamily: font.displayBold, color: colors.gold, fontSize: 10, letterSpacing: 1},
  title: {fontFamily: font.displayBold, color: colors.white, fontSize: 25, marginTop: 2},
  tabs: {gap: 8, paddingRight: 18},
  tab: {paddingHorizontal: 13, paddingVertical: 9, borderRadius: 8, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border},
  tabActive: {backgroundColor: colors.gold, borderColor: colors.gold},
  tabText: {fontFamily: font.display, color: colors.muted, fontSize: 12},
  tabTextActive: {color: colors.base},
  podium: {flexDirection: 'row', alignItems: 'flex-end', gap: 7, minHeight: 235},
  podiumItem: {flex: 1, minWidth: 0, alignItems: 'center', padding: 8, paddingTop: 13, borderRadius: 10, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border},
  first: {paddingTop: 19, paddingBottom: 17, borderColor: '#7a6515', backgroundColor: '#182b40'},
  place: {fontFamily: font.displayBold, color: colors.gold, fontSize: 15, marginBottom: 7},
  player: {width: '100%', fontFamily: font.displayBold, color: colors.white, fontSize: 12, textAlign: 'center', marginTop: 8},
  team: {width: '100%', fontFamily: font.body, color: colors.muted, fontSize: 9, textAlign: 'center', marginTop: 2},
  score: {fontFamily: font.displayBold, color: colors.gold, fontSize: 25, marginTop: 7},
  unit: {fontFamily: font.displayBold, color: colors.muted, fontSize: 8},
  list: {paddingVertical: 5},
  listRow: {minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: colors.border},
  listPlace: {width: 22, fontFamily: font.displayBold, color: colors.muted, fontSize: 16, textAlign: 'center'},
  listCopy: {flex: 1},
  listName: {fontFamily: font.display, color: colors.white, fontSize: 14},
  listTeam: {fontFamily: font.body, color: colors.muted, fontSize: 10, marginTop: 2},
  listValue: {fontFamily: font.displayBold, color: colors.gold, fontSize: 19},
  note: {fontFamily: font.body, color: colors.muted, fontSize: 11, lineHeight: 16, textAlign: 'center'},
});
