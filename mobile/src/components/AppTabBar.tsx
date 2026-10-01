import type { BottomTabBarProps } from 'expo-router/build/react-navigation/bottom-tabs/types';
import { Ionicons } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, font, webBaseUrl } from '@/theme';

const metadata: Record<string, {label: string; icon: keyof typeof Ionicons.glyphMap}> = {
  index: {label: 'Inicio', icon: 'american-football-outline'},
  standings: {label: 'Posiciones', icon: 'bar-chart-outline'},
  leaders: {label: 'Líderes', icon: 'trophy-outline'},
  stats: {label: 'Mis Stats', icon: 'stats-chart-outline'},
};

export function AppTabBar({state, navigation}: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.bar, {paddingBottom: Math.max(insets.bottom, 8)}]}>
      {state.routes.map((route, index) => {
        const item = metadata[route.name];
        if (!item) return null;
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
      <Pressable
        accessibilityLabel="Abrir perfil en la versión web"
        accessibilityRole="link"
        onPress={() => void WebBrowser.openBrowserAsync(`${webBaseUrl}/dashboard`)}
        style={styles.item}
      >
        <Ionicons name="person-circle-outline" size={23} color={colors.muted} />
        <Text style={styles.label}>Perfil</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {flexDirection: 'row', paddingTop: 10, paddingHorizontal: 4, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: '#020f23'},
  item: {flex: 1, minHeight: 52, alignItems: 'center', justifyContent: 'center', gap: 3},
  label: {fontFamily: font.displayBold, fontSize: 9, color: colors.muted, letterSpacing: 0.5},
  labelActive: {color: colors.gold},
});
