import { Ionicons } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { absoluteMediaUrl } from '@/lib/api';
import { colors, font, webBaseUrl } from '@/theme';

export function Avatar({name, url, size = 46}: {name: string; url?: string | null; size?: number}) {
  const source = absoluteMediaUrl(url);
  if (source) {
    return <Image source={{uri: source}} style={{width: size, height: size, borderRadius: size / 2}} />;
  }
  return (
    <View style={[styles.avatarFallback, {width: size, height: size, borderRadius: size / 2}]}>
      <Text style={styles.avatarText}>{name.trim().slice(0, 1).toUpperCase()}</Text>
    </View>
  );
}

export function TeamLogo({name, url, size = 42}: {name: string; url?: string | null; size?: number}) {
  const source = absoluteMediaUrl(url);
  if (source) return <Image source={{uri: source}} style={{width: size, height: size, borderRadius: 8}} resizeMode="contain" />;
  return (
    <View style={[styles.teamFallback, {width: size, height: size}]}>
      <Ionicons name="shield-half-outline" size={Math.round(size * 0.55)} color={colors.gold} />
    </View>
  );
}

export function WebLink({path, label, icon = 'open-outline'}: {path: string; label: string; icon?: keyof typeof Ionicons.glyphMap}) {
  return (
    <Pressable onPress={() => void WebBrowser.openBrowserAsync(`${webBaseUrl}${path}`)} style={({pressed}) => [styles.webLink, pressed && styles.pressed]}>
      <Ionicons name={icon} color={colors.gold} size={18} />
      <Text style={styles.webLinkText}>{label}</Text>
      <Ionicons name="chevron-forward" color={colors.muted} size={16} />
    </Pressable>
  );
}

export function Metric({label, value, accent = false}: {label: string; value: string | number; accent?: boolean}) {
  return (
    <View style={styles.metric}>
      <Text style={[styles.metricValue, accent && styles.metricAccent]}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  avatarFallback: {alignItems: 'center', justifyContent: 'center', backgroundColor: '#23405e', borderWidth: 2, borderColor: colors.gold},
  avatarText: {fontFamily: font.displayBold, color: colors.white, fontSize: 20},
  teamFallback: {alignItems: 'center', justifyContent: 'center', borderRadius: 8, backgroundColor: colors.cardHigh},
  webLink: {minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 10, borderRadius: 8, paddingHorizontal: 14, backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border},
  webLinkText: {flex: 1, fontFamily: font.display, fontSize: 14, color: colors.text},
  pressed: {opacity: 0.75},
  metric: {flex: 1, minWidth: 72, alignItems: 'center', justifyContent: 'center', paddingVertical: 13, paddingHorizontal: 7, borderRadius: 8, backgroundColor: colors.cardHigh},
  metricValue: {fontFamily: font.displayBold, fontSize: 23, color: colors.white},
  metricAccent: {color: colors.gold},
  metricLabel: {fontFamily: font.bodyMedium, color: colors.muted, fontSize: 10, textAlign: 'center', marginTop: 3, textTransform: 'uppercase'},
});
