import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, post } from '../api/client';
import { Empty, ErrorNotice, Loading, PageHeader, money } from '../components/UI';
import { useResource } from '../hooks/useResource';
import type { Asset, Quote, Watchlist } from '../types';

type Item = { asset: Asset; comment: string; tags: string; position: number; added_at: string };
function Row({ item, remove }: { item: Item; remove: () => void }) { const { data } = useResource<Quote>(`/assets/${item.asset.id}/quote`); return <tr><td><Link to={`/asset/${item.asset.id}`}><strong>{item.asset.symbol}</strong><small>{item.asset.name}</small></Link></td><td>{money(data?.price, item.asset.currency)}</td><td>{data?.change_percent == null ? 'No disponible' : `${Number(data.change_percent).toFixed(2)}%`}</td><td>{money(data?.market_cap, item.asset.currency)}</td><td>{item.asset.sector ?? 'No disponible'}</td><td>{item.tags || '—'}</td><td>{data?.date ?? '—'}<small>{data?.provider ?? 'Sin proveedor'}</small></td><td><button onClick={remove} aria-label={`Quitar ${item.asset.symbol}`}>Quitar</button></td></tr>; }
export function Watchlists() {
  const lists = useResource<Watchlist[]>('/watchlists');
  const [selected, setSelected] = useState('');
  const id = selected || lists.data?.[0]?.id;
  const items = useResource<Item[]>(id ? `/watchlists/${id}/items` : null);
  const [error, setError] = useState('');
  async function remove(assetId: string) { if (!window.confirm('¿Quitar este activo de la watchlist?')) return; try { await api(`/watchlists/${id}/items/${assetId}`, { method: 'DELETE' }); items.reload(); } catch (e) { setError((e as Error).message); } }
  return <><PageHeader eyebrow="SEGUIMIENTO" title="Tus watchlists"><Link to="/assets">Explorar activos →</Link></PageHeader><ErrorNotice error={error || lists.error || items.error} /><section className="panel"><form className="search-box" onSubmit={async e => { e.preventDefault(); const form = e.currentTarget; try { const w = await post<Watchlist>('/watchlists', { name: new FormData(form).get('name') }); lists.reload(); setSelected(w.id); form.reset(); } catch (err) { setError((err as Error).message); } }}><input name="name" aria-label="Nombre de watchlist" placeholder="Nombre de la nueva watchlist" maxLength={128} required /><button className="primary">Crear watchlist</button></form></section><div className="tabs">{lists.data?.map(l => <button key={l.id} onClick={() => setSelected(l.id)} className={id === l.id ? 'selected' : ''}>{l.name}</button>)}</div><section className="panel">{items.loading ? <Loading /> : items.data?.length ? <div className="table-wrap"><table><thead><tr><th>ACTIVO</th><th>PRECIO</th><th>CAMBIO</th><th>MARKET CAP</th><th>SECTOR</th><th>ETIQUETAS</th><th>ÚLTIMO DATO</th><th /></tr></thead><tbody>{items.data.map(i => <Row key={i.asset.id} item={i} remove={() => remove(i.asset.id)} />)}</tbody></table></div> : <Empty title="Una lista para tus próximas ideas"><p>Crea una watchlist y añade activos desde su página de detalle.</p></Empty>}</section></>;
}
