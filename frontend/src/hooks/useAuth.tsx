import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, post, setCsrf } from '../api/client';
import type { User } from '../types';

type Auth = { user: User | null; loading: boolean; login: (username: string, password: string) => Promise<void>; logout: () => Promise<void> };
const AuthContext = createContext<Auth | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api<User>('/auth/me').then(u => { setCsrf(u.csrf_token); setUser(u); }).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  async function login(username: string, password: string) {
    const u = await post<User>('/auth/login', { username, password });
    setCsrf(u.csrf_token); setUser(u);
  }
  async function logout() { await post('/auth/logout'); setCsrf(''); setUser(null); }
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error('AuthProvider required'); return context; }
