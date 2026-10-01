import { Tabs } from 'expo-router';

import { AppTabBar } from '@/components/AppTabBar';

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{headerShown: false}} tabBar={(props) => <AppTabBar {...props} />}>
      <Tabs.Screen name="index" options={{title: 'Inicio'}} />
      <Tabs.Screen name="standings" options={{title: 'Posiciones'}} />
      <Tabs.Screen name="leaders" options={{title: 'Líderes'}} />
      <Tabs.Screen name="stats" options={{title: 'Mis Stats'}} />
    </Tabs>
  );
}

