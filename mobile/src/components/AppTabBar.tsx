import type { BottomTabBarProps } from 'expo-router/build/react-navigation/bottom-tabs/types';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, font } from '@/theme';
import { useAuth } from '@/providers/AuthProvider';

const metadata: Record<string, {label: string; icon: keyof typeof Ionicons.glyphMap}> = {
  index: {label: 'Inicio', icon: 'american-football-outline'},
  standings: {label: 'Posiciones', icon: 'bar-chart-outline'},
  leaders: {label: 'Líderes', icon: 'trophy-outline'},
  stats: {label: 'Mis Stats', icon: 'stats-chart-outline'},
  assignments: {label: 'Mi agenda', icon: 'calendar-outline'},
  history: {label: 'Historial', icon: 'time-outline'},
  profile: {label: 'Mi perfil', icon: 'person-circle-outline'},
};

export function AppTabBar({state, navigation}: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const {mode} = useAuth();
  const visible = mode === 'referee' ? ['index', 'assignments', 'history', 'profile'] : ['index', 'standings', 'leaders', 'stats', 'profile'];
  return (
    <View style={[styles.bar, {paddingBottom: Math.max(insets.bottom, 8)}]}>
      {state.routes.map((route, index) => {
        const item = metadata[route.name];
        if (!item || !visible.includes(route.name)) return null;
        const focused = state.index === index;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{selected: focused}}
            key={route.key}
            onPress={() => navigation.navigate(route.name, route.params)}
            style={styles.item}
          >
            <Ionicons name={item.icon} size={22} color={focused ? colors.gold : colors.muted} />
            <Text style={[styles.label, focused && styles.labelActive]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {flexDirection: 'row', paddingTop: 10, paddingHorizontal: 4, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: '#020f23'},
  item: {flex: 1, minHeight: 52, alignItems: 'center', justifyContent: 'center', gap: 3},
  label: {fontFamily: font.displayBold, fontSize: 9, color: colors.muted, letterSpacing: 0.5},
  labelActive: {color: colors.gold},
});
