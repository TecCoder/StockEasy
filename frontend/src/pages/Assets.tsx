import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { api, post } from '../api/client';
import { Empty, ErrorNotice, Loading, PageHeader } from '../components/UI';
import { useResource } from '../hooks/useResource';
import type { Asset } from '../types';

export function Assets({ crypto = false }: { crypto?: boolean }) {
  const local = useResource<Asset[]>('/assets');
  const [results, setResults] = useState<Asset[] | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState(false);
  const navigate = useNavigate();
  async function search(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(''); const q = new FormData(event.currentTarget).get('q'); try { const data = await api<{ items: Asset[]; warnings: string[] }>(`/assets/search?q=${encodeURIComponent(String(q))}${crypto ? '&asset_type=CRYPTO' : ''}`); setResults(data.items); setWarnings(data.warnings); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  async function add(asset: Partial<Asset>) { setError(''); try { const a = await post<Asset>('/assets', { ...asset, cik: asset.cik || null }); navigate(`/asset/${a.id}`); } catch (e) { setError((e as Error).message); } }
  const rows = (results ?? local.data ?? []).filter(a => !crypto || a.asset_type === 'CRYPTO');
  return <><PageHeader eyebrow="RESEARCH" title={crypto ? 'Explorar crypto' : 'Explorar activos'}><button onClick={() => setManual(!manual)}><Plus size={16} />Activo manual</button></PageHeader><ErrorNotice error={error || local.error} /><section className="panel"><form className="search-box" onSubmit={search}><Search size={19} className="muted" /><input name="q" aria-label="Buscar activos" placeholder="Busca por ticker o nombre: AAPL, Apple, Bitcoin…" required /><button className="primary" disabled={busy}>Buscar</button></form></section>{warnings.length > 0 && <details className="notice"><summary>Disponibilidad de los proveedores ({warnings.length})</summary>{warnings.map(w => <p key={w}>{w}</p>)}</details>}{manual && <section className="panel"><h2>Añadir activo manual</h2><form onSubmit={e => { e.preventDefault(); void add(Object.fromEntries(new FormData(e.currentTarget))); }}><div className="form-grid"><label>Ticker / ISIN<input name="symbol" required maxLength={64} /></label><label>Nombre<input name="name" required /></label><label>Tipo<select name="asset_type" defaultValue={crypto ? 'CRYPTO' : 'STOCK'}>{['STOCK','ETF','MUTUAL_FUND','CRYPTO'].map(t => <option key={t}>{t}</option>)}</select></label><label>Moneda<input name="currency" defaultValue="EUR" maxLength={3} required /></label><label>Mercado / identificador<input name="exchange" defaultValue="MANUAL" required /></label><label>CIK (SEC, opcional)<input name="cik" pattern="[0-9]{1,10}" /></label></div><button className="primary">Guardar activo</button></form></section>}<section className="panel"><div className="panel-heading"><h2>{results ? 'Resultados de búsqueda' : 'Tus activos'}</h2><span className="badge">{rows.length} ACTIVOS</span></div>{busy || local.loading ? <Loading /> : rows.length ? <div className="table-wrap"><table><thead><tr><th>ACTIVO</th><th>TIPO</th><th>MERCADO</th><th>MONEDA</th><th>FUENTE</th><th /></tr></thead><tbody>{rows.map((a, i) => <tr key={`${a.id ?? a.provider_asset_id}-${i}`}><td><strong>{a.symbol}</strong><small>{a.name}</small></td><td>{a.asset_type}</td><td>{a.exchange}</td><td>{a.currency}</td><td>{a.provider ?? 'Local'}</td><td>{a.id ? <Link to={`/asset/${a.id}`}>Ver activo →</Link> : <button onClick={() => add(a)}>Añadir</button>}</td></tr>)}</tbody></table></div> : <Empty title={results ? 'No se encontraron activos' : 'Tu universo de inversión'}><p>Busca un activo o añádelo manualmente. Configura tus proveedores para consultar datos de mercado.</p></Empty>}</section></>;
}
