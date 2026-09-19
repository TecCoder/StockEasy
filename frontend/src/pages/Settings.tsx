import { useEffect, useState, type FormEvent } from 'react';
import { api, post, put } from '../api/client';
import { ErrorNotice, PageHeader } from '../components/UI';
import type { Preferences } from '../types';

export function Settings() {
  const [prefs, setPrefs] = useState<Preferences>({ theme: 'dark', base_currency: 'EUR' });
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  useEffect(() => { api<Preferences>('/settings').then(setPrefs).catch(e => setError(e.message)); }, []);
  async function save(event: FormEvent) { event.preventDefault(); setError(''); setSaved(false); try { await put('/settings', prefs); document.documentElement.dataset.theme = prefs.theme; setSaved(true); } catch (e) { setError((e as Error).message); } }
  async function password(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); try { await post('/auth/password', Object.fromEntries(data)); window.location.reload(); } catch (e) { setError((e as Error).message); } }
  return <><PageHeader eyebrow="WORKSPACE" title="Configuración" /><ErrorNotice error={error} /><div className="two-col"><section className="panel"><h2>Preferencias</h2><form onSubmit={save}><label>Apariencia<select value={prefs.theme} onChange={e => setPrefs({ ...prefs, theme: e.target.value as Preferences['theme'] })}><option value="dark">Oscura</option><option value="light">Clara</option></select></label><label>Moneda base<select value={prefs.base_currency} onChange={e => setPrefs({ ...prefs, base_currency: e.target.value })}>{['EUR', 'USD', 'GBP', 'JPY', 'CHF'].map(c => <option key={c}>{c}</option>)}</select></label><button className="primary">Guardar preferencias</button>{saved && <span role="status" className="accent">Guardado</span>}</form></section><section className="panel"><h2>Seguridad</h2><p className="muted">Al cambiar la contraseña se cerrarán todas tus sesiones.</p><form onSubmit={password}><label>Contraseña actual<input name="current_password" type="password" autoComplete="current-password" required /></label><label>Nueva contraseña<input name="new_password" type="password" autoComplete="new-password" minLength={12} maxLength={256} required /></label><button>Cambiar contraseña</button></form></section></div><section className="panel"><h2>Claves de proveedores</h2><p className="muted">Configura las claves en el archivo .env del proyecto y reinicia el backend. Las claves nunca se envían al navegador.</p></section></>;
}
