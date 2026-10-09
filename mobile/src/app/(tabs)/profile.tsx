import { useState } from 'react';
import { useRouter } from 'expo-router';
import { Pressable, Text } from 'react-native';
import { Avatar, WebLink } from '@/components/LeagueUI';
import { Panel, Screen } from '@/components/Screen';
import { useAuth } from '@/providers/AuthProvider';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import { colors, font } from '@/theme';

export default function ProfileScreen() {
  const {user, mode, setMode, signOut} = useAuth();
  const {refereeProfile, dashboard} = useLeagueData();
  const router = useRouter();
  const [error, setError] = useState('');
  const profile = mode === 'referee' ? refereeProfile : dashboard?.player;
  const dualRole = user?.roles.includes('player') && user.roles.includes('referee');
  return <Screen title="Mi perfil">
    <Panel style={{gap: 12, alignItems: 'center'}}>
      <Avatar name={user?.name || ''} url={profile?.profile_photo_url} size={72} />
      <Text style={{color: colors.white, fontFamily: font.displayBold, fontSize: 24}}>{user?.display_name || user?.name}</Text>
      <Text style={{color: colors.gold}}>Vista de {mode === 'referee' ? 'árbitro' : 'jugador'}</Text>
    </Panel>
    {dualRole ? <Pressable accessibilityRole="button" onPress={() => {router.replace('/'); setMode(mode === 'referee' ? 'player' : 'referee');}} style={{padding: 18, backgroundColor: colors.card, borderRadius: 10}}>
      <Text style={{color: colors.gold, fontFamily: font.display}}>Cambiar a {mode === 'referee' ? 'jugador' : 'árbitro'}</Text>
    </Pressable> : null}
    <WebLink path={mode === 'referee' ? '/referee/games' : '/dashboard'} label="Administrar perfil en la web" />
    {error ? <Text style={{color: colors.danger}}>{error}</Text> : null}
    <Pressable accessibilityRole="button" onPress={() => void signOut().catch(() => setError('No se pudo cerrar sesión. Intenta de nuevo.'))} style={{padding: 18}}>
      <Text style={{color: colors.danger, fontFamily: font.display}}>Cerrar sesión</Text>
    </Pressable>
  </Screen>;
}
