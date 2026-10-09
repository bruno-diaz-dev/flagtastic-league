import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { loadCurrentUser, mobileLogin, mobileLogout } from '@/lib/api';
import { clearToken, getStoredToken, saveToken } from '@/lib/storage';
import {availableModes, defaultMode, type MobileMode} from '@/lib/mobileRoles';
import type { User } from '@/types';

type AuthValue = {
  token: string | null;
  user: User | null;
  loading: boolean;
  error: string;
  mode: MobileMode;
  setMode: (mode: MobileMode) => void;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<MobileMode>('player');

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
        const nextMode = defaultMode(currentUser.roles || []);
        if (!nextMode) throw new Error('Cuenta sin acceso móvil.');
        setMode(nextMode);
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
      const nextMode = defaultMode(result.user.roles || []);
      if (!nextMode) throw new Error('Cuenta sin acceso móvil.');
      await saveToken(result.access_token);
      setToken(result.access_token);
      setUser(result.user);
      setMode(nextMode);
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
    () => ({token, user, loading, error, mode, setMode: (nextMode: MobileMode) => {
      if (user && availableModes(user.roles).includes(nextMode)) setMode(nextMode);
    }, signIn, signOut}),
    [token, user, loading, error, mode],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
