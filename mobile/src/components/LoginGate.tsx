import { FormEvent, PropsWithChildren, useState } from 'react';
import { ActivityIndicator, Image, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { useAuth } from '@/providers/AuthProvider';
import { colors, font } from '@/theme';

export function LoginGate({ children }: PropsWithChildren) {
  const { token, loading, error, signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!email || password.length < 8) return;
    await signIn(email, password).catch(() => undefined);
  }

  if (loading && !token) {
    return <View style={styles.center}><ActivityIndicator color={colors.gold} size="large" /><Text style={[styles.copy, {marginTop: 16}]}>Conectando con tu cuenta…</Text></View>;
  }
  if (token) return children;

  return (
    <KeyboardAvoidingView style={styles.page} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={styles.brand}>
        <Image source={require('../../assets/flagtastic.jpeg')} style={styles.logo} />
        <Text style={styles.eyebrow}>FLAGTASTIC LEAGUE</Text>
        <Text style={styles.title}>Tu temporada, en el bolsillo.</Text>
        <Text style={styles.copy}>Entra con tu cuenta de jugador, árbitro o representante de la liga.</Text>
      </View>
      <View style={styles.panel}>
        <Text style={styles.label}>CORREO</Text>
        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder="tu@correo.com"
          placeholderTextColor="#556f91"
          style={styles.input}
          value={email}
        />
        <Text style={styles.label}>CONTRASEÑA</Text>
        <TextInput
          autoComplete="current-password"
          onChangeText={setPassword}
          onSubmitEditing={() => void submit()}
          placeholder="••••••••"
          placeholderTextColor="#556f91"
          secureTextEntry
          style={styles.input}
          value={password}
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Pressable
          accessibilityRole="button"
          disabled={!email || password.length < 8 || loading}
          onPress={() => void submit()}
          style={({pressed}) => [styles.button, pressed && styles.pressed]}
        >
          {loading ? <ActivityIndicator color={colors.base} /> : <Text style={styles.buttonText}>INICIAR SESIÓN</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {flex: 1, justifyContent: 'center', padding: 24, backgroundColor: colors.background},
  center: {flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background},
  brand: {alignItems: 'center', marginBottom: 28},
  logo: {width: 88, height: 88, borderRadius: 18, marginBottom: 14},
  eyebrow: {fontFamily: font.displayBold, fontSize: 12, color: colors.gold, letterSpacing: 1.3},
  title: {fontFamily: font.displayBold, fontSize: 28, color: colors.white, textAlign: 'center', marginTop: 8},
  copy: {fontFamily: font.body, fontSize: 14, color: colors.muted, textAlign: 'center', marginTop: 8},
  panel: {padding: 18, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card},
  label: {fontFamily: font.displayBold, color: colors.muted, fontSize: 11, marginBottom: 6, letterSpacing: 1},
  input: {height: 50, borderRadius: 8, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, color: colors.white, paddingHorizontal: 14, fontFamily: font.body, fontSize: 16, marginBottom: 16},
  button: {height: 52, alignItems: 'center', justifyContent: 'center', borderRadius: 8, backgroundColor: colors.gold, marginTop: 4},
  buttonText: {fontFamily: font.displayBold, color: colors.base, fontSize: 15, letterSpacing: 0.6},
  pressed: {opacity: 0.82},
  error: {fontFamily: font.body, color: colors.danger, marginBottom: 12},
});

