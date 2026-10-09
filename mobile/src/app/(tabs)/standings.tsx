import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { TeamLogo } from '@/components/LeagueUI';
import { EmptyState, Panel, Pill, Screen } from '@/components/Screen';
import { DivisionFilter } from '@/components/DivisionFilter';
import { useDivisionData } from '@/lib/useDivisionData';
import { loadStandings } from '@/lib/api';
import { colors, font } from '@/theme';

export default function StandingsScreen() {
  const query = useDivisionData(loadStandings);
  const {division, setDivision, team, data: standings = [], refreshing, error} = query;

  return (
    <Screen title="Posiciones" refreshControl={query}>
      <DivisionFilter division={division} onChange={setDivision} team={team} />
      <Panel style={styles.division}>
        <View><Text style={styles.kicker}>DIVISIÓN SELECCIONADA</Text><Text style={styles.title}>{division.branch.toUpperCase()} · {division.category.toUpperCase()}</Text></View>
        <Pill>JORNADA ACTUAL</Pill>
      </Panel>
      {refreshing ? <ActivityIndicator accessibilityLabel="Cargando posiciones" color={colors.gold} /> : null}
      {!refreshing && !error && !standings.length ? <EmptyState title="Sin resultados" copy="Aún no hay posiciones para esta rama y categoría." /> : null}
      {standings.length > 0 ? <View style={styles.table}>
        <View style={styles.headerRow}>
          <Text style={[styles.headerText, styles.rank]}>#</Text><Text style={[styles.headerText, styles.club]}>EQUIPO</Text><Text style={styles.headerText}>G</Text><Text style={styles.headerText}>P</Text><Text style={styles.headerText}>DIF</Text>
        </View>
        {standings.map((row, index) => {
          const current = row.team_id === team?.team_id;
          return (
            <View key={row.team_id} style={[styles.row, current && styles.current]}>
              <View style={styles.rankCell}><Text style={[styles.rankValue, current && styles.currentText]}>{index + 1}</Text></View>
              <View style={styles.clubCell}>
                <TeamLogo name={row.team_name} url={row.team_logo_url} size={36} />
                <View style={styles.clubCopy}><Text numberOfLines={1} style={styles.clubName}>{row.team_name}</Text>{current ? <Text style={styles.you}>TU EQUIPO</Text> : null}</View>
              </View>
              <Text style={styles.value}>{row.wins}</Text><Text style={styles.value}>{row.losses}</Text><Text style={[styles.value, row.point_difference > 0 && styles.positive]}>{row.point_difference > 0 ? '+' : ''}{row.point_difference}</Text>
            </View>
          );
        })}
      </View> : null}
      <Panel>
        <Text style={styles.rulesTitle}>CRITERIOS DE DESEMPATE</Text>
        <Text style={styles.rules}>1. Partidos ganados  ·  2. Diferencia de puntos  ·  3. Puntos anotados  ·  4. Menos derrotas</Text>
      </Panel>
    </Screen>
  );
}

const styles = StyleSheet.create({
  division: {flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between'},
  kicker: {fontFamily: font.displayBold, color: colors.gold, fontSize: 10, letterSpacing: 1},
  title: {fontFamily: font.displayBold, color: colors.white, fontSize: 21, marginTop: 3},
  table: {overflow: 'hidden', borderWidth: 1, borderColor: colors.border, borderRadius: 10, backgroundColor: colors.card},
  headerRow: {height: 38, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, backgroundColor: '#092352'},
  headerText: {width: 39, fontFamily: font.displayBold, color: colors.muted, fontSize: 10, textAlign: 'center'},
  rank: {width: 28},
  club: {flex: 1, textAlign: 'left'},
  row: {minHeight: 64, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, borderTopWidth: 1, borderTopColor: colors.border},
  current: {backgroundColor: '#17304d', borderLeftWidth: 3, borderLeftColor: colors.gold},
  rankCell: {width: 28},
  rankValue: {fontFamily: font.displayBold, color: colors.muted, fontSize: 17},
  currentText: {color: colors.gold},
  clubCell: {flex: 1, flexDirection: 'row', alignItems: 'center', gap: 9, paddingRight: 5},
  clubCopy: {flex: 1},
  clubName: {fontFamily: font.display, color: colors.white, fontSize: 14},
  you: {fontFamily: font.displayBold, color: colors.gold, fontSize: 8, marginTop: 2},
  value: {width: 39, fontFamily: font.bodyMedium, color: colors.text, textAlign: 'center', fontSize: 13},
  positive: {color: colors.cyan},
  rulesTitle: {fontFamily: font.displayBold, color: colors.gold, fontSize: 11, letterSpacing: 0.7},
  rules: {fontFamily: font.body, color: colors.muted, fontSize: 12, lineHeight: 19, marginTop: 7},
});
