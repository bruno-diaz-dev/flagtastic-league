import { useState } from 'react';
import { useRouter } from 'expo-router';
import { Pressable, Text } from 'react-native';
import { Avatar, WebLink } from '@/components/LeagueUI';
import { Panel, Screen } from '@/components/Screen';
import { useAuth } from '@/providers/AuthProvider';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import {availableModes, modeLabels} from '@/lib/mobileRoles';
import { colors, font } from '@/theme';

export default function ProfileScreen() {
  const {user, mode, setMode, signOut} = useAuth();
  const {refereeProfile, dashboard} = useLeagueData();
  const router = useRouter();
  const [error, setError] = useState('');
  const profile = mode === 'referee' ? refereeProfile : mode === 'player' ? dashboard?.player : null;
  const otherModes = availableModes(user?.roles || []).filter(next => next !== mode);
  return <Screen title="Mi perfil">
    <Panel style={{gap: 12, alignItems: 'center'}}>
      <Avatar name={user?.name || ''} url={profile?.profile_photo_url} size={72} />
      <Text style={{color: colors.white, fontFamily: font.displayBold, fontSize: 24}}>{user?.display_name || user?.name}</Text>
      <Text style={{color: colors.gold}}>Vista de {modeLabels[mode]}</Text>
    </Panel>
    {otherModes.map(next => <Pressable key={next} accessibilityRole="button" onPress={() => {router.replace('/'); setMode(next);}} style={{padding: 18, backgroundColor: colors.card, borderRadius: 10}}>
      <Text style={{color: colors.gold, fontFamily: font.display}}>Cambiar a {modeLabels[next]}</Text>
    </Pressable>)}
    <WebLink path={mode === 'representative' ? '/representative-dashboard' : mode === 'referee' ? '/referee/games' : '/dashboard'} label="Administrar perfil en la web" />
    {error ? <Text style={{color: colors.danger}}>{error}</Text> : null}
    <Pressable accessibilityRole="button" onPress={() => void signOut().catch(() => setError('No se pudo cerrar sesión. Intenta de nuevo.'))} style={{padding: 18}}>
      <Text style={{color: colors.danger, fontFamily: font.display}}>Cerrar sesión</Text>
    </Pressable>
  </Screen>;
}
