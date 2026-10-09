import { useEffect, useState } from 'react';
import { Slot } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useFonts } from 'expo-font';
import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { SpaceGrotesk_600SemiBold } from '@expo-google-fonts/space-grotesk/600SemiBold';
import { SpaceGrotesk_700Bold } from '@expo-google-fonts/space-grotesk/700Bold';

import { LoginGate } from '@/components/LoginGate';
import { AuthProvider } from '@/providers/AuthProvider';
import { LeagueDataProvider } from '@/providers/LeagueDataProvider';
import { colors } from '@/theme';

void SplashScreen.preventAutoHideAsync().catch(() => undefined);

export default function RootLayout() {
  const [loaded, fontError] = useFonts({Inter_400Regular, Inter_600SemiBold, SpaceGrotesk_600SemiBold, SpaceGrotesk_700Bold});
  const [timedOut, setTimedOut] = useState(false);
  const [continueWithoutFonts, setContinueWithoutFonts] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), 15000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (loaded || fontError || timedOut) void SplashScreen.hideAsync().catch(() => undefined);
  }, [loaded, fontError, timedOut]);

  if (!loaded && !continueWithoutFonts) {
    if (!fontError && !timedOut) return null;
    return <View style={styles.recovery}>
      <Text style={styles.message}>La descarga de las fuentes está tardando demasiado.</Text>
      <Pressable accessibilityRole="button" style={styles.button} onPress={() => setContinueWithoutFonts(true)}>
        <Text style={styles.message}>Continuar con la app</Text>
      </Pressable>
    </View>;
  }
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

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: colors.background},
  recovery: {flex: 1, justifyContent: 'center', padding: 28, gap: 20, backgroundColor: colors.background},
  message: {color: colors.white, fontSize: 17, textAlign: 'center'},
  button: {padding: 18, backgroundColor: colors.cardHigh, borderRadius: 10},
});
