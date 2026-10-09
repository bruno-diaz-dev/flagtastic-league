import { useCallback, useEffect, useRef, useState } from 'react';
import { useLeagueData } from '@/providers/LeagueDataProvider';
import { normalizeDivision, type Division } from '@/lib/divisions';

export function useDivisionData<T>(load: (branch: string, category: string) => Promise<T>) {
  const {activeTeam} = useLeagueData();
  const team = activeTeam || undefined;
  const [selection, setSelection] = useState<Division | null>(null);
  const division = normalizeDivision(selection || team || {branch: 'varonil', category: 'libre'});
  const {branch, category} = division;
  const key = `${branch}/${category}`;
  const [result, setResult] = useState<{key: string; data?: T; error: string}>({key: '', error: ''});
  const [refreshing, setRefreshing] = useState(false);
  const requestId = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++requestId.current;
    setRefreshing(true);
    setResult({key, error: ''});
    try {
      const data = await load(branch, category);
      if (id === requestId.current) setResult({key, data, error: ''});
    } catch (error) {
      if (id === requestId.current) setResult({key, error: error instanceof Error ? error.message : 'No se pudo cargar esta división.'});
    } finally {
      if (id === requestId.current) setRefreshing(false);
    }
  }, [branch, category, key, load]);
  useEffect(() => {
    void refresh();
    return () => { requestId.current += 1; };
  }, [refresh]);
  return {
    division, setDivision: setSelection, team,
    data: result.key === key ? result.data : undefined,
    error: result.key === key ? result.error : '',
    refreshing: refreshing || result.key !== key, refresh,
  };
}
