import { Tabs } from 'expo-router';

import { AppTabBar } from '@/components/AppTabBar';
import { useAuth } from '@/providers/AuthProvider';

export default function TabsLayout() {
  const {mode} = useAuth();
  return (
    <Tabs key={mode} initialRouteName="index" screenOptions={{headerShown: false}} tabBar={(props) => <AppTabBar {...props} />}>
      <Tabs.Screen name="index" options={{title: 'Inicio'}} />
      <Tabs.Protected guard={mode === 'player' || mode === 'representative'}>
        <Tabs.Screen name="standings" options={{title: 'Posiciones'}} />
        <Tabs.Screen name="leaders" options={{title: 'Líderes'}} />
      </Tabs.Protected>
      <Tabs.Protected guard={mode === 'player'}>
        <Tabs.Screen name="stats" options={{title: 'Mis Stats'}} />
      </Tabs.Protected>
      <Tabs.Protected guard={mode === 'representative'}>
        <Tabs.Screen name="teams" options={{title: 'Mis equipos'}} />
        <Tabs.Screen name="team-games" options={{title: 'Partidos'}} />
      </Tabs.Protected>
      <Tabs.Protected guard={mode === 'referee'}>
        <Tabs.Screen name="assignments" options={{title: 'Mi agenda'}} />
        <Tabs.Screen name="history" options={{title: 'Historial'}} />
      </Tabs.Protected>
      <Tabs.Screen name="profile" options={{title: 'Mi perfil'}} />
    </Tabs>
  );
}

