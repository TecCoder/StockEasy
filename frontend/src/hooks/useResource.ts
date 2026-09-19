import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

export function useResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(r => r + 1), []);
  useEffect(() => {
    let active = true; setData(null); setError('');
    if (!path) { setLoading(false); return; }
    setLoading(true);
    api<T>(path).then(d => { if (active) setData(d); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, revision]);
  return { data, error, loading, reload };
}
