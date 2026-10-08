import { PropsWithChildren, ReactNode } from 'react';
import * as WebBrowser from 'expo-web-browser';
import { Image, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useLeagueData } from '@/providers/LeagueDataProvider';
import { useAuth } from '@/providers/AuthProvider';
import { colors, font, webBaseUrl } from '@/theme';

export function Screen({ title, children }: PropsWithChildren<{title: string}>) {
  const {refresh, refreshing, error, dashboard, activeTeam, selectTeam} = useLeagueData();
  const {signOut} = useAuth();
  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Image source={require('../../assets/flagtastic.jpeg')} style={styles.logo} />
        <View style={styles.headerCopy}>
          <View style={styles.brandRow}><Text style={styles.brand}>FLAGTASTIC</Text><View style={styles.liveDot} /></View>
          <Text style={styles.title}>{title}</Text>
        </View>
        <Pressable accessibilityLabel="Abrir perfil web" onPress={() => void WebBrowser.openBrowserAsync(`${webBaseUrl}/dashboard`)} style={styles.headerButton}>
          <Ionicons name="person-outline" size={21} color={colors.gold} />
        </Pressable>
        <Pressable accessibilityLabel="Cerrar sesión" onPress={() => void signOut()} style={styles.headerButton}>
          <Ionicons name="log-out-outline" size={21} color={colors.text} />
        </Pressable>
      </View>
      {dashboard && dashboard.teams.length > 1 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.teamSwitcher} contentContainerStyle={styles.teamSwitcherContent}>
          {dashboard.teams.map((team) => {
            const selected = team.team_id === activeTeam?.team_id;
            return (
              <Pressable key={team.team_id} onPress={() => void selectTeam(team.team_id)} style={[styles.teamChoice, selected && styles.teamChoiceActive]}>
                <Text style={[styles.teamChoiceText, selected && styles.teamChoiceTextActive]}>{team.team_name} · {team.category.toUpperCase()}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}
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
  teamSwitcher: {flexGrow: 0, borderBottomWidth: 1, borderBottomColor: colors.border, backgroundColor: colors.background},
  teamSwitcherContent: {gap: 8, paddingHorizontal: 18, paddingVertical: 9},
  teamChoice: {paddingHorizontal: 12, paddingVertical: 8, borderRadius: 7, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface},
  teamChoiceActive: {borderColor: colors.gold, backgroundColor: '#3e3826'},
  teamChoiceText: {fontFamily: font.display, color: colors.muted, fontSize: 11},
  teamChoiceTextActive: {color: colors.gold},
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
