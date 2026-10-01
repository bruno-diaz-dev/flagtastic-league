import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import { loadCurrentUser, mobileLogin } from '@/lib/api';
import { clearToken, getStoredToken, saveToken } from '@/lib/storage';
import type { User } from '@/types';

type AuthValue = {
  token: string | null;
  user: User | null;
  loading: boolean;
  error: string;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getStoredToken().then(async (storedToken) => {
      if (!storedToken) return;
      try {
        const currentUser = await loadCurrentUser(storedToken);
        if (!(currentUser.roles || []).includes('player')) throw new Error('Cuenta sin perfil de jugador.');
        setToken(storedToken);
        setUser(currentUser);
      } catch {
        await clearToken();
      }
    }).finally(() => setLoading(false));
  }, []);

  async function signIn(email: string, password: string) {
    setError('');
    setLoading(true);
    try {
      const result = await mobileLogin(email.trim(), password);
      await saveToken(result.access_token);
      setToken(result.access_token);
      setUser(result.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo iniciar sesión.');
      throw caught;
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await clearToken();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({token, user, loading, error, signIn, signOut}),
    [token, user, loading, error],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}

