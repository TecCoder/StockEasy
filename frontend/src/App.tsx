import { useEffect, useRef, useState } from "react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  Activity,
  Bitcoin,
  LayoutDashboard,
  Menu,
  Power,
  Search,
  Settings as SettingsIcon,
  ShieldCheck,
  Star,
  Wallet,
  X,
} from "lucide-react";
import { api } from "./api/client";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { Empty, Loading } from "./components/UI";
import { Login } from "./pages/Login";
import { Settings } from "./pages/Settings";
import { Assets } from "./pages/Assets";
import { AssetDetail } from "./pages/AssetDetail";
import { Watchlists } from "./pages/Watchlists";
import { Providers } from "./pages/Providers";
import { Portfolio } from "./pages/Portfolio";
import { Dashboard } from "./pages/Dashboard";
import type { DisplayCurrency, Preferences } from "./types";

function Workspace() {
  const { user, loading, shutdown } = useAuth();
  const [error, setError] = useState("");
  const [closing, setClosing] = useState(false);
  const menu = useRef<HTMLDialogElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  useEffect(() => {
    menu.current?.close();
  }, [location]);
  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 761px)");
    const closeOnDesktop = () => {
      if (desktop.matches) menu.current?.close();
    };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);
  const [displayCurrency, setDisplayCurrency] = useState<DisplayCurrency>(() =>
    localStorage.getItem("stockeasy-display-currency") === "USD"
      ? "USD"
      : "EUR",
  );
  function changeDisplayCurrency(currency: DisplayCurrency) {
    setDisplayCurrency(currency);
    localStorage.setItem("stockeasy-display-currency", currency);
  }
  useEffect(() => {
    if (user)
      api<Preferences>("/settings")
        .then((p) => {
          document.documentElement.dataset.theme = p.theme;
        })
        .catch(() => {});
  }, [user]);
  if (loading) return <Loading />;
  if (!user) return <Login />;
  const links = [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/watchlists", icon: Star, label: "Watchlists" },
    { to: "/portfolio", icon: Wallet, label: "Portfolio" },
    { to: "/assets", icon: Search, label: "Explorar activos" },
    { to: "/crypto", icon: Bitcoin, label: "Explorar crypto" },
    { to: "/providers", icon: Activity, label: "Estado de datos" },
    { to: "/settings", icon: SettingsIcon, label: "Configuración" },
  ];
  async function closeApplication() {
    setClosing(true);
    setError("");
    try {
      await shutdown();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo cerrar la aplicación",
      );
      setClosing(false);
    }
  }
  const navigation = (
    <>
      <NavLink to="/" className="brand" onClick={() => menu.current?.close()}>
        <span className="brand-icon">▥</span>StockEasy
      </NavLink>
      <p className="nav-caption">INVESTMENT WORKSPACE</p>
      <nav aria-label="Navegación principal">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={() => menu.current?.close()}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="local-status">
          <ShieldCheck size={17} />
          <div>
            Almacenamiento local<small>Tus datos, en tu equipo</small>
          </div>
        </div>
        <div className="user-row">
          <span className="avatar">{user.username[0].toUpperCase()}</span>
          <span>
            {user.username}
            <small>Cuenta personal</small>
          </span>
          <button
            className="exit-button"
            title="Cerrar sesión y apagar StockEasy"
            disabled={closing}
            onClick={closeApplication}
          >
            <Power size={16} />
            {closing ? "Cerrando…" : "Salir"}
          </button>
        </div>
        {error && <p role="alert">{error}</p>}
      </div>
    </>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">{navigation}</aside>
      <dialog
        ref={menu}
        id="mobile-navigation"
        className="mobile-navigation"
        aria-label="Menú principal"
        onClose={() => setMenuOpen(false)}
        onClick={(event) => {
          if (event.target === event.currentTarget) menu.current?.close();
        }}
      >
        <div className="mobile-navigation-content">
          <button
            className="menu-close"
            aria-label="Cerrar menú"
            onClick={() => menu.current?.close()}
          >
            <X size={20} />
          </button>
          {navigation}
        </div>
      </dialog>
      <div className="main-wrap">
        <header className="topbar">
          <button
            className="menu-toggle"
            aria-label="Abrir menú"
            aria-controls="mobile-navigation"
            aria-expanded={menuOpen}
            onClick={() => {
              menu.current?.showModal();
              setMenuOpen(true);
            }}
          >
            <Menu size={20} />
            <span>StockEasy</span>
          </button>
          <span className="workspace-label">
            Workspace <span className="muted">/ Personal</span>
          </span>
          <div>
            <span className="workspace-status">
              <span className="status-dot" /> Local · EOD
            </span>
            <div
              className="currency-toggle"
              aria-label="Moneda de visualización"
            >
              {(["EUR", "USD"] as DisplayCurrency[]).map((currency) => (
                <button
                  key={currency}
                  className={displayCurrency === currency ? "selected" : ""}
                  onClick={() => changeDisplayCurrency(currency)}
                >
                  {currency}
                </button>
              ))}
            </div>
          </div>
        </header>
        <main className="content">
          <Routes>
            <Route
              path="/"
              element={<Dashboard displayCurrency={displayCurrency} />}
            />
            <Route path="/settings" element={<Settings />} />
            <Route path="/assets" element={<Assets />} />
            <Route path="/crypto" element={<Assets crypto />} />
            <Route path="/asset/:id" element={<AssetDetail />} />
            <Route path="/watchlists" element={<Watchlists />} />
            <Route path="/providers" element={<Providers />} />
            <Route
              path="/portfolio"
              element={<Portfolio displayCurrency={displayCurrency} />}
            />
            <Route
              path="*"
              element={
                <Empty title="Sección en preparación">
                  <p>Consulta el roadmap de desarrollo.</p>
                </Empty>
              }
            />
          </Routes>
        </main>
        <footer>
          Financial data is provided for informational purposes only. This
          application does not provide investment advice.
        </footer>
      </div>
    </div>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Workspace />
      </AuthProvider>
    </BrowserRouter>
  );
}
