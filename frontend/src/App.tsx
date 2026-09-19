import { useEffect, useState } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import { LayoutDashboard, Star, Wallet, Search, Settings as SettingsIcon, LogOut, Activity, ShieldCheck } from 'lucide-react';
import { api } from './api/client';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Empty, Loading, Metric, PageHeader } from './components/UI';
import { Login } from './pages/Login';
import { Settings } from './pages/Settings';
import { Assets } from './pages/Assets';
import { AssetDetail } from './pages/AssetDetail';
import { Watchlists } from './pages/Watchlists';
import { Providers } from './pages/Providers';
import type { Preferences } from './types';

function Dashboard() { return <><PageHeader eyebrow="VISTA GENERAL" title="Tu inversión, en perspectiva" /><div className="metrics"><Metric label="Valor de cartera" value="—" hint="Crea una cartera para empezar" /><Metric label="Capital invertido" value="—" /><Metric label="Pérdidas y ganancias" value="—" /><Metric label="Efectivo" value="—" /></div><section className="panel"><div className="panel-heading"><h2>Evolución de tu cartera</h2><span className="badge">SIN OPERACIONES</span></div><Empty title="Tu historial empieza aquí"><p>Añade tu primera cartera y registra tus operaciones.</p></Empty></section></>; }

function Workspace() {
  const { user, loading, logout } = useAuth();
  const [error, setError] = useState('');
  useEffect(() => { if (user) api<Preferences>('/settings').then(p => { document.documentElement.dataset.theme = p.theme; }).catch(() => {}); }, [user]);
  if (loading) return <Loading />;
  if (!user) return <Login />;
  const links = [{ to: '/', icon: LayoutDashboard, label: 'Dashboard' }, { to: '/watchlists', icon: Star, label: 'Watchlists' }, { to: '/portfolio', icon: Wallet, label: 'Portfolio' }, { to: '/assets', icon: Search, label: 'Explorar activos' }, { to: '/providers', icon: Activity, label: 'Estado de datos' }, { to: '/settings', icon: SettingsIcon, label: 'Configuración' }];
  return <div className="app-shell"><aside className="sidebar"><NavLink to="/" className="brand"><span className="brand-icon">▥</span>StockEasy</NavLink><p className="nav-caption">INVESTMENT WORKSPACE</p><nav>{links.map(({ to, icon: Icon, label }) => <NavLink key={to} to={to} end={to === '/'}><Icon size={18} />{label}</NavLink>)}</nav><div className="sidebar-bottom"><div className="local-status"><ShieldCheck size={17} /><div>Almacenamiento local<small>Tus datos, en tu equipo</small></div></div><div className="user-row"><span className="avatar">{user.username[0].toUpperCase()}</span><span>{user.username}<small>Cuenta personal</small></span><button className="icon-button" title="Cerrar sesión" onClick={() => logout().catch(e => setError(e.message))}><LogOut size={17} /></button></div>{error && <p role="alert">{error}</p>}</div></aside><div className="main-wrap"><header className="topbar"><span>Workspace <span className="muted">/ Personal</span></span><div><span className="status-dot" />Local · EOD <span className="badge">EUR</span></div></header><main className="content"><Routes><Route path="/" element={<Dashboard />} /><Route path="/settings" element={<Settings />} /><Route path="/assets" element={<Assets />} /><Route path="/crypto" element={<Assets crypto />} /><Route path="/asset/:id" element={<AssetDetail />} /><Route path="/watchlists" element={<Watchlists />} /><Route path="/providers" element={<Providers />} /><Route path="*" element={<Empty title="Sección en preparación"><p>Consulta el roadmap de desarrollo.</p></Empty>} /></Routes></main><footer>Financial data is provided for informational purposes only. This application does not provide investment advice.</footer></div></div>;
}
export default function App() { return <BrowserRouter><AuthProvider><Workspace /></AuthProvider></BrowserRouter>; }

