import { PropsWithChildren, ReactNode } from 'react';
import { Image, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useLeagueData } from '@/providers/LeagueDataProvider';
import { colors, font } from '@/theme';

export function Screen({ title, children }: PropsWithChildren<{title: string}>) {
  const {refresh, refreshing, error} = useLeagueData();
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Image source={require('../../assets/flagtastic.jpeg')} style={styles.logo} />
        <View style={styles.headerCopy}>
          <View style={styles.brandRow}><Text style={styles.brand}>FLAGTASTIC</Text><View style={styles.liveDot} /></View>
          <Text style={styles.title}>{title}</Text>
        </View>
        <View style={styles.headerButton}><Ionicons name="sunny" size={22} color={colors.gold} /></View>
        <View style={styles.headerButton}><Ionicons name="notifications" size={21} color={colors.text} /><View style={styles.noticeDot} /></View>
      </View>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} tintColor={colors.gold} />}
        showsVerticalScrollIndicator={false}
      >
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {children}
      </ScrollView>
    </View>
  );
}

export function SectionTitle({ icon, children, aside }: PropsWithChildren<{icon?: keyof typeof Ionicons.glyphMap; aside?: ReactNode}>) {
  return (
    <View style={styles.sectionTitle}>
      <View style={styles.sectionTitleCopy}>
        {icon ? <Ionicons name={icon} size={20} color={colors.gold} /> : null}
        <Text style={styles.sectionTitleText}>{children}</Text>
      </View>
      {aside}
    </View>
  );
}

export function Panel({children, style}: PropsWithChildren<{style?: object}>) {
  return <View style={[styles.panel, style]}>{children}</View>;
}

export function Pill({children, tone = 'gold'}: PropsWithChildren<{tone?: 'gold' | 'orange' | 'muted'}>) {
  const toneStyle = tone === 'orange' ? styles.pillOrange : tone === 'muted' ? styles.pillMuted : styles.pillGold;
  return <View style={[styles.pill, toneStyle]}><Text style={[styles.pillText, tone === 'orange' && styles.orangeText]}>{children}</Text></View>;
}

export function EmptyState({title, copy}: {title: string; copy: string}) {
  return <Panel style={styles.empty}><Ionicons name="american-football-outline" size={30} color={colors.muted} /><Text style={styles.emptyTitle}>{title}</Text><Text style={styles.emptyCopy}>{copy}</Text></Panel>;
}

const styles = StyleSheet.create({
  root: {flex: 1, backgroundColor: colors.background},
  header: {height: 66, paddingHorizontal: 18, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: 1, borderBottomColor: '#0b2440', backgroundColor: colors.background},
  logo: {width: 34, height: 34, borderRadius: 17},
  headerCopy: {flex: 1},
  brandRow: {flexDirection: 'row', alignItems: 'center', gap: 5},
  brand: {fontFamily: font.displayBold, fontSize: 10, color: colors.gold},
  liveDot: {width: 5, height: 5, borderRadius: 3, backgroundColor: colors.orange},
  title: {fontFamily: font.display, fontSize: 20, color: colors.white, lineHeight: 22},
  headerButton: {width: 42, height: 42, borderRadius: 10, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center'},
  noticeDot: {position: 'absolute', right: 8, top: 7, width: 7, height: 7, borderRadius: 4, backgroundColor: colors.orange},
  content: {padding: 18, paddingBottom: 112, gap: 18},
  error: {fontFamily: font.body, color: colors.danger, padding: 12, backgroundColor: '#3b1c26', borderRadius: 8},
  panel: {borderRadius: 10, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card, padding: 16},
  sectionTitle: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  sectionTitleCopy: {flexDirection: 'row', alignItems: 'center', gap: 8},
  sectionTitleText: {fontFamily: font.display, fontSize: 20, color: colors.text},
  pill: {paddingVertical: 4, paddingHorizontal: 9, borderRadius: 999, alignSelf: 'flex-start'},
  pillGold: {backgroundColor: '#3e3826'},
  pillOrange: {backgroundColor: '#43282a'},
  pillMuted: {backgroundColor: colors.cardHigh},
  pillText: {fontFamily: font.displayBold, fontSize: 10, color: colors.gold, letterSpacing: 0.6},
  orangeText: {color: colors.orange},
  empty: {alignItems: 'center', gap: 8, paddingVertical: 30},
  emptyTitle: {fontFamily: font.display, color: colors.text, fontSize: 18},
  emptyCopy: {fontFamily: font.body, color: colors.muted, fontSize: 13, textAlign: 'center'},
});

