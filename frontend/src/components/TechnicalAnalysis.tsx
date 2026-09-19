import { useMemo, useState } from 'react';
import { useResource } from '../hooks/useResource';
import { PriceChart, type Series } from './PriceChart';
import type { Price } from '../types';

type Indicators = { dates: string[]; series: Record<string, (number | null)[]>; warning?: string };
const COLORS = ['#e9b56e', '#8ab7ed', '#d396ed', '#7adacb', '#e6dd78'];
export function TechnicalAnalysis({ assetId, prices }: { assetId: string; prices: Price[] }) {
  const { data } = useResource<Indicators>(`/assets/${assetId}/indicators`);
  const [enabled, setEnabled] = useState<string[]>(['SMA50', 'SMA200']);
  const overlays = useMemo(() => enabled.filter(n => n !== 'RSI14' && !n.startsWith('MACD')).map((name, index): Series => ({ name, color: COLORS[index % COLORS.length], points: data?.dates.flatMap((time, i) => { const value = data.series[name]?.[i]; return value != null && prices.some(p => p.date === time) ? [{ time, value }] : []; }) ?? [] })), [data, enabled, prices]);
  const rsi = useMemo(() => data?.dates.flatMap((date, i) => data.series.RSI14?.[i] != null && prices.some(p => p.date === date) ? [{ date, close: String(data.series.RSI14[i]), open: null, high: null, low: null, volume: null, provider: 'calculated', retrieved_at: '', adjustment: 'indicator' }] : []) ?? [], [data, prices]);
  const macd = useMemo(() => data?.dates.flatMap((date, i) => data.series.MACD_macd?.[i] != null && prices.some(p => p.date === date) ? [{ date, close: String(data.series.MACD_macd[i]), open: null, high: null, low: null, volume: null, provider: 'calculated', retrieved_at: '', adjustment: 'indicator' }] : []) ?? [], [data, prices]);
  return <><div className="toolbar">{['SMA20','SMA50','SMA100','SMA200','EMA20','EMA50','EMA200','BB_upper','BB_lower','RSI14','MACD_macd'].map(n => <label key={n}><input type="checkbox" checked={enabled.includes(n)} onChange={e => setEnabled(e.target.checked ? [...enabled, n] : enabled.filter(v => v !== n))} />{n.replace('BB_', 'Bollinger ').replace('MACD_macd', 'MACD')}</label>)}</div><PriceChart prices={prices} overlays={overlays} />{overlays.some(s => !s.points.length) && <p className="muted">Histórico insuficiente para {overlays.filter(s => !s.points.length).map(s => s.name).join(', ')}.</p>}{enabled.includes('RSI14') && <><h3>RSI 14 · Wilder</h3>{rsi.length ? <PriceChart prices={rsi} height={160} /> : <p className="muted">Datos insuficientes para RSI.</p>}</>}{enabled.includes('MACD_macd') && <><h3>MACD · 12 / 26 / 9</h3>{macd.length ? <PriceChart prices={macd} height={160} overlays={[{ name: 'Signal', color: '#e9b56e', points: data?.dates.flatMap((time, i) => data.series.MACD_signal?.[i] != null && prices.some(p => p.date === time) ? [{ time, value: data.series.MACD_signal[i]! }] : []) ?? [] }]} /> : <p className="muted">Datos insuficientes para MACD.</p>}</>}<small>Indicadores calculados sobre toda la serie antes de seleccionar el rango. Precios sin ajustar pueden mostrar discontinuidades por splits.</small></>;
}
