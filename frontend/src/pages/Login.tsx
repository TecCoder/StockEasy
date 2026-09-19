import { useState, type FormEvent } from 'react';
import { ArrowUpRight, LockKeyhole } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { ErrorNotice } from '../components/UI';

export function Login() {
  const { login } = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try { await login(String(form.get('username')), String(form.get('password'))); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="login-layout"><section className="login-story"><a className="brand" href="/"><span className="brand-icon">▥</span> StockEasy<span className="badge">LOCAL</span></a><div><p className="eyebrow">TU ESPACIO DE INVERSIÓN</p><h1>Perspectiva para<br />cada decisión<span>.</span></h1><p>Investiga empresas, sigue tus activos y entiende cómo evoluciona tu cartera.</p><div className="login-feature"><span>01</span> Datos con una fuente clara <ArrowUpRight size={18} /></div><div className="login-feature"><span>02</span> Tu historial, bajo tu control <ArrowUpRight size={18} /></div><div className="login-feature"><span>03</span> Todo en tu equipo <ArrowUpRight size={18} /></div></div><small>Acciones · ETFs · Fondos · Crypto</small></section><section className="login-panel"><div className="login-box"><LockKeyhole className="accent" size={26} /><h2>Bienvenido a tu workspace</h2><p className="muted">Accede con tu cuenta local.</p><ErrorNotice error={error} /><form onSubmit={submit}><label>Usuario<input autoComplete="username" name="username" required autoFocus /></label><label>Contraseña<input autoComplete="current-password" name="password" type="password" required /></label><button className="primary" disabled={busy}>{busy ? 'Entrando…' : 'Iniciar sesión'}<ArrowUpRight size={18} /></button></form><details><summary>¿Es tu primera vez?</summary><p>Crea tu usuario desde el terminal del proyecto:</p><code>python -m app.cli create-user --username tu_usuario</code><p>Consulta el README para activar el entorno e iniciar la aplicación. No hay una contraseña predeterminada.</p></details></div><small className="disclaimer">Financial data is provided for informational purposes only.<br />This application does not provide investment advice.</small></section></main>;
}
