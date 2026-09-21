import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Empty, ErrorNotice, Loading, PageHeader, money, number } from '../components/UI';
import { useResource } from '../hooks/useResource';
import { PortfolioSummary, type PortfolioInfo, type Snapshot } from './Portfolio';

export function Dashboard() {
  const portfolios = useResource<PortfolioInfo[]>('/portfolios');
  const [selected, setSelected] = useState('');
  const current = portfolios.data?.find(portfolio => portfolio.id === selected) ?? portfolios.data?.[0];
  const snapshot = useResource<Snapshot>(current ? `/portfolios/${current.id}/positions` : null);

  return <>
    <PageHeader eyebrow="VISTA GENERAL" title="Tu inversión, en perspectiva">
      <Link to="/portfolio">Abrir portfolio →</Link>
    </PageHeader>
    <ErrorNotice error={portfolios.error || snapshot.error} />
    {portfolios.loading ? <Loading /> : !portfolios.data?.length ? <section className="panel"><Empty title="Tu historial empieza aquí"><p>Crea una cartera y registra tus operaciones para ver el resumen.</p><Link to="/portfolio">Crear cartera →</Link></Empty></section> : <>
      <div className="tabs">{portfolios.data.map(portfolio => <button key={portfolio.id} className={current?.id === portfolio.id ? 'selected' : ''} onClick={() => setSelected(portfolio.id)}>{portfolio.name} · {portfolio.base_currency}</button>)}</div>
      {snapshot.loading ? <Loading /> : snapshot.data && <>
        <PortfolioSummary data={snapshot.data} />
        <section className="panel">
          <div className="panel-heading"><h2>Posiciones actuales</h2><span className="badge">{snapshot.data.positions.length} POSICIONES</span></div>
          {snapshot.data.positions.length ? <div className="table-wrap"><table><thead><tr><th>ACTIVO</th><th>CANTIDAD</th><th>PRECIO ACTUAL</th><th>VALOR</th><th>P/L LATENTE</th><th>PESO</th></tr></thead><tbody>{snapshot.data.positions.map(position => <tr key={position.asset_id}><td><Link to={`/asset/${position.asset_id}`}><strong>{position.symbol}</strong><small>{position.name}</small></Link></td><td>{number(position.quantity, 8)}</td><td>{money(position.current_price, position.currency)}</td><td>{money(position.current_value, snapshot.data!.base_currency)}</td><td>{money(position.unrealized_pl, snapshot.data!.base_currency)}</td><td>{position.weight == null ? '—' : `${number(position.weight)}%`}</td></tr>)}</tbody></table></div> : <Empty title="Todavía no tienes posiciones"><p>Registra una compra o transferencia de entrada en esta cartera.</p></Empty>}
        </section>
      </>}
    </>}
  </>;
}
