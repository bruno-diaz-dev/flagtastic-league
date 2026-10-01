import { useEffect } from 'react';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StyleSheet } from 'react-native';
import {
  Inter_400Regular,
  Inter_600SemiBold,
  useFonts as useInterFonts,
} from '@expo-google-fonts/inter';
import {
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
  useFonts as useSpaceFonts,
} from '@expo-google-fonts/space-grotesk';

import { LoginGate } from '@/components/LoginGate';
import { AuthProvider } from '@/providers/AuthProvider';
import { LeagueDataProvider } from '@/providers/LeagueDataProvider';
import { colors } from '@/theme';

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [interLoaded] = useInterFonts({Inter_400Regular, Inter_600SemiBold});
  const [spaceLoaded] = useSpaceFonts({SpaceGrotesk_600SemiBold, SpaceGrotesk_700Bold});

  useEffect(() => {
    if (interLoaded && spaceLoaded) void SplashScreen.hideAsync();
  }, [interLoaded, spaceLoaded]);

  if (!interLoaded || !spaceLoaded) return null;
  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe} edges={['top']}>
        <AuthProvider>
          <LoginGate>
            <LeagueDataProvider><Slot /></LeagueDataProvider>
          </LoginGate>
        </AuthProvider>
        <StatusBar style="light" />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({safe: {flex: 1, backgroundColor: colors.background}});
