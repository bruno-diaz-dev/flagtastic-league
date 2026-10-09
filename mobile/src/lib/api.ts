import Constants from 'expo-constants';

import type { Game, Leaderboards, PlayerDashboard, Standing, User } from '@/types';

const configuredUrl = process.env.EXPO_PUBLIC_API_URL
  || Constants.expoConfig?.extra?.apiBaseUrl
  || 'https://flagtastic.online';

export const apiBaseUrl = String(configuredUrl).replace(/\/$/, '');

export function absoluteMediaUrl(path?: string | null) {
  if (!path) return null;
  return path.startsWith('http') ? path : `${apiBaseUrl}${path}`;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function parseError(response: Response) {
  const body = await response.json().catch(() => ({}));
  if (typeof body.detail === 'string') return body.detail;
  return `No se pudo completar la solicitud (${response.status}).`;
}

export async function apiRequest<T>(path: string, token?: string | null, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && typeof init.body === 'string') headers.set('Content-Type', 'application/json');
  const response = await fetch(`${apiBaseUrl}${path}`, {...init, headers});
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function mobileLogin(email: string, password: string) {
  return apiRequest<{
    access_token: string;
    token_type: string;
    expires_at: string;
    user: User;
  }>('/api/auth/mobile/login', null, {
    method: 'POST',
    body: JSON.stringify({email, password}),
  });
}

export function loadCurrentUser(token: string) {
  return apiRequest<User>('/api/auth/me', token);
}

export function mobileLogout(token: string) {
  return apiRequest<void>('/api/auth/logout', token, {method: 'POST'});
}

export function loadDashboard(token: string) {
  return apiRequest<PlayerDashboard>('/api/me/dashboard', token);
}

export function loadGames(token: string) {
  return apiRequest<Game[]>('/api/games', token);
}

export function loadStandings(branch: string, category: string) {
  const query = new URLSearchParams({branch, category}).toString();
  return apiRequest<Standing[]>(`/api/standings?${query}`);
}

export function loadLeaderboards(branch: string, category: string) {
  const query = new URLSearchParams({branch, category}).toString();
  return apiRequest<Leaderboards>(`/api/statistics/leaderboards?${query}`);
}
