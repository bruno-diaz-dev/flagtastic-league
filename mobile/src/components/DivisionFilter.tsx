import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Panel } from '@/components/Screen';
import { branches, categories, normalizeDivision, type Division } from '@/lib/divisions';
import { colors, font } from '@/theme';

export function DivisionFilter({division, onChange, team}: {division: Division; onChange: (value: Division) => void; team?: Division}) {
  const unified = ['u8', 'u10', 'u12'].includes(division.category);
  return <Panel style={{gap: 12}}>
    <View style={styles.row}><Text style={styles.label}>CONSULTAR DIVISIÓN</Text>{team ? <Pressable accessibilityRole="button" onPress={() => onChange(normalizeDivision(team))} style={styles.reset}><Text style={styles.resetText}>Mi división</Text></Pressable> : null}</View>
    <Text style={styles.label}>CATEGORÍA</Text>
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap: 8}}>
      {categories.map(category => <Pressable key={category} accessibilityRole="button" accessibilityState={{selected: division.category === category}} onPress={() => onChange(normalizeDivision({...division, category}))} style={[styles.chip, division.category === category && styles.active]}><Text style={[styles.text, division.category === category && styles.activeText]}>{category.toUpperCase()}</Text></Pressable>)}
    </ScrollView>
    <Text style={styles.label}>RAMA</Text>
    <View style={styles.row}>{(unified ? ['mixto'] : branches).map(branch => <Pressable key={branch} accessibilityRole="button" accessibilityState={{selected: division.branch === branch}} onPress={() => onChange({...division, branch})} style={[styles.chip, division.branch === branch && styles.active]}><Text style={[styles.text, division.branch === branch && styles.activeText]}>{branch.toUpperCase()}</Text></Pressable>)}</View>
    {unified ? <Text style={styles.note}>Esta categoría reúne a todos los equipos en una sola tabla.</Text> : null}
  </Panel>;
}
const styles = StyleSheet.create({
  row: {flexDirection: 'row', gap: 8, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between'},
  label: {fontFamily: font.displayBold, color: colors.muted, fontSize: 11},
  chip: {paddingHorizontal: 12, minHeight: 44, justifyContent: 'center', borderRadius: 8, backgroundColor: colors.cardHigh},
  active: {backgroundColor: colors.gold},
  text: {fontFamily: font.display, fontSize: 12, color: colors.text},
  activeText: {color: colors.base},
  reset: {minHeight: 44, justifyContent: 'center', paddingHorizontal: 8},
  resetText: {color: colors.gold, fontFamily: font.display, fontSize: 13},
  note: {color: colors.muted, fontFamily: font.body, fontSize: 12},
});
