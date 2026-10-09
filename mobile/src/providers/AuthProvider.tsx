import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { loadCurrentUser, mobileLogin, mobileLogout } from '@/lib/api';
import { clearToken, getStoredToken, saveToken } from '@/lib/storage';
import type { User } from '@/types';

type AuthValue = {
  token: string | null;
  user: User | null;
  loading: boolean;
  error: string;
  mode: 'player' | 'referee';
  setMode: (mode: 'player' | 'referee') => void;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'player' | 'referee'>('player');

  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      if (!active) return;
      active = false;
      setError('No se pudo recuperar la sesión a tiempo. Puedes iniciar sesión de nuevo.');
      setLoading(false);
    }, 20000);
    async function restoreSession() {
      try {
        const storedToken = await getStoredToken();
        if (!storedToken || !active) return;
        const currentUser = await loadCurrentUser(storedToken);
        if (!active) return;
        if (!currentUser.roles?.some(role => role === 'player' || role === 'referee')) throw new Error('Cuenta sin acceso móvil.');
        setMode(currentUser.roles.includes('referee') ? 'referee' : 'player');
        setToken(storedToken);
        setUser(currentUser);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : 'No se pudo recuperar la sesión. Intenta iniciar sesión de nuevo.');
      } finally {
        clearTimeout(timer);
        if (active) setLoading(false);
      }
    }
    void restoreSession();
    return () => {active = false; clearTimeout(timer);};
  }, []);

  async function signIn(email: string, password: string) {
    setError('');
    setLoading(true);
    try {
      const result = await mobileLogin(email.trim(), password);
      await saveToken(result.access_token);
      setToken(result.access_token);
      setUser(result.user);
      setMode(result.user.roles.includes('referee') ? 'referee' : 'player');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo iniciar sesión.');
      throw caught;
    } finally {
      setLoading(false);
    }
  }

  const signOut = useCallback(async () => {
    if (token) await mobileLogout(token).catch(() => undefined);
    await clearToken();
    setToken(null);
    setUser(null);
  }, [token]);

  const value = useMemo(
    () => ({token, user, loading, error, mode, setMode, signIn, signOut}),
    [token, user, loading, error, mode],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
