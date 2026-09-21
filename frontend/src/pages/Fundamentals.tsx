import { useMemo, useState } from 'react';
import { useResource } from '../hooks/useResource';
import { compactNumber, Empty, ErrorNotice, Loading, number } from '../components/UI';
import { PriceChart, type ChartValueFormat } from '../components/PriceChart';

type Fact = { value: string | null; unit: string; provider?: string; filed?: string; period_end?: string; retrieved_at?: string; fiscal_period?: string; source_concept?: string; accession?: string; formula?: string; calculated: boolean; inputs?: Fact[] };
type Data = { period: string; latest: Record<string, Fact>; history: { date: string; metrics: Record<string, Fact> }[]; warning?: string };
const labels: Record<string,string> = { revenue: 'Ingresos', net_income: 'Beneficio neto', eps: 'EPS diluido', eps_basic: 'EPS básico', operating_cash_flow: 'Cash flow operativo', capex: 'CapEx', fcf: 'Free cash flow', gross_profit: 'Beneficio bruto', operating_income: 'Beneficio operativo', gross_margin: 'Margen bruto', operating_margin: 'Margen operativo', net_margin: 'Margen neto', cash: 'Efectivo', assets: 'Activos', equity: 'Patrimonio neto', long_term_debt: 'Deuda a largo plazo', short_term_debt: 'Deuda a corto plazo', current_debt: 'Vencimientos de deuda', shares: 'Acciones en circulación', sbc: 'Remuneración en acciones', dividends_paid: 'Dividendos pagados', buybacks: 'Recompras', current_assets: 'Activo corriente', current_liabilities: 'Pasivo corriente', inventory: 'Inventario' };

function readableUnit(unit: string | undefined): string {
  if (!unit) return 'Sin unidad';
  if (unit === 'ratio') return 'Porcentaje (%)';
  if (unit === 'shares') return 'Acciones';
  if (unit.endsWith('/shares')) return `${unit.split('/')[0]} por acción`;
  return `Importe (${unit})`;
}

function factValue(fact: Fact | undefined): string {
  if (fact?.value == null) return 'No disponible';
  if (fact.unit === 'ratio') return `${number(Number(fact.value) * 100, 1)} %`;
  if (fact.unit.endsWith('/shares')) return number(fact.value, 4);
  return compactNumber(fact.value);
}

function chartFormat(unit: string | undefined): ChartValueFormat {
  if (unit === 'ratio') return 'percent';
  if (unit?.endsWith('/shares')) return 'number';
  return 'compact';
}

export function Fundamentals({ assetId }: { assetId: string }) {
  const [period, setPeriod] = useState('annual');
  const [metric, setMetric] = useState('revenue');
  const state = useResource<Data>(`/assets/${assetId}/fundamentals?period=${period}`);
  const valuation = useResource<{ warning: string; historical_pe: unknown[] }>(`/assets/${assetId}/valuation`);
  const prices = useMemo(() => state.data?.history.flatMap(r => r.metrics[metric]?.value != null ? [{ date: r.date, close: r.metrics[metric].value!, open: null, high: null, low: null, volume: null, provider: r.metrics[metric].provider ?? 'calculated', adjustment: '', retrieved_at: '' }] : []) ?? [], [state.data, metric]);
  const selectedFact = state.data?.latest[metric] ?? state.data?.history.flatMap(row => row.metrics[metric] ? [row.metrics[metric]] : []).at(-1);
  const selectedUnit = selectedFact?.unit ?? '';
  const chartUnit = selectedUnit === 'shares' ? 'acciones' : selectedUnit.endsWith('/shares') ? `${selectedUnit.split('/')[0]}/acción` : selectedUnit === 'ratio' ? '' : selectedUnit;
  const selectedHistory = [...(state.data?.history ?? [])].reverse().flatMap(row => row.metrics[metric] ? [{ date: row.date, fact: row.metrics[metric] }] : []);
  return <><section className="panel"><div className="panel-heading"><h2>Fundamentales · SEC EDGAR</h2><div className="tabs"><button className={period === 'annual' ? 'selected' : ''} onClick={() => setPeriod('annual')}>Annual</button><button className={period === 'quarterly' ? 'selected' : ''} onClick={() => setPeriod('quarterly')}>Quarterly</button></div></div><ErrorNotice error={state.error} />{state.data?.warning && <div className="notice">{state.data.warning}</div>}{state.loading ? <Loading /> : Object.keys(state.data?.latest ?? {}).length ? <><div className="toolbar"><label>Métrica<select value={metric} onChange={e => setMetric(e.target.value)}>{Object.entries(labels).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>{prices.length ? <PriceChart prices={prices} height={270} axisLabel={readableUnit(selectedUnit)} seriesLabel={labels[metric]} unit={chartUnit} valueFormat={chartFormat(selectedUnit)} /> : <Empty title="Datos no disponibles para esta métrica" />}{selectedHistory.length > 0 && <div className="historical-facts"><h3>Histórico · {labels[metric]}</h3><div className="table-wrap"><table><thead><tr><th>PERÍODO</th><th>VALOR</th><th>UNIDAD</th><th>PRESENTADO</th></tr></thead><tbody>{selectedHistory.map(({ date, fact }) => <tr key={`${date}-${fact.accession ?? fact.filed ?? ''}`}><td>{date}</td><td title={`Valor exacto: ${number(fact.value, 8)}`}>{factValue(fact)}</td><td>{fact.unit === 'ratio' ? '%' : fact.unit === 'shares' ? 'acciones' : fact.unit.replace('/shares', '/acción')}</td><td>{fact.filed ?? fact.inputs?.map(value => value.filed).filter(Boolean).join(', ') ?? '—'}</td></tr>)}</tbody></table></div></div>}<h3>Último reporte disponible</h3><div className="table-wrap"><table><thead><tr><th>MÉTRICA</th><th>VALOR ABREVIADO</th><th>UNIDAD / PERÍODO</th><th>TRAZABILIDAD</th></tr></thead><tbody>{Object.entries(labels).map(([key,label]) => { const f = state.data?.latest[key]; return <tr key={key}><td>{label}</td><td title={f?.value != null ? `Valor exacto: ${number(f.value, 8)}` : undefined}>{factValue(f)}</td><td>{f?.unit === 'ratio' ? '%' : f?.unit === 'shares' ? 'acciones' : f?.unit?.replace('/shares', '/acción') ?? '—'}<small>{f?.period_end ?? '—'}</small></td><td>{f && <details><summary>{f.calculated ? 'Calculado · ver fórmula' : 'SEC EDGAR · ver fuente'}</summary><p>{f.formula ?? f.source_concept}<br />Presentado: {f.filed ?? f.inputs?.map(v => v.filed).join(', ')}<br />Descargado: {f.retrieved_at ?? f.inputs?.[0]?.retrieved_at}<br />Accession: {f.accession ?? f.inputs?.map(v => v.accession).join(', ')}</p></details>}</td></tr>; })}</tbody></table></div></> : <Empty title="Fundamentales no disponibles"><p>Configura SEC_USER_AGENT y el CIK de la compañía. No todos los conceptos XBRL tienen una equivalencia comparable.</p></Empty>}</section><section className="panel"><h2>Valoración histórica y peers</h2><p className="muted">{valuation.data?.warning ?? 'Cargando metodología…'}</p><div className="metrics">{['P/E TTM','Forward P/E','P/E histórico','Mediana sectorial'].map(n => <div className="metric" key={n}><span>{n}</span><strong style={{fontSize:15}}>No disponible</strong></div>)}</div><small>Un universo sectorial requiere compañías identificadas, fechas compatibles y tamaño de muestra suficiente. No se generan señales BUY/SELL.</small></section></>;
}
