import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, post, put } from "../api/client";
import { PriceChart } from "../components/PriceChart";
import {
  Empty,
  ErrorNotice,
  Loading,
  Metric,
  PageHeader,
  money,
  number,
} from "../components/UI";
import { useResource } from "../hooks/useResource";
import type { Asset, DisplayCurrency, Price } from "../types";

export type PortfolioInfo = { id: string; name: string; base_currency: string };
export type Transaction = {
  id: string;
  asset_id: string | null;
  date: string;
  executed_at: string | null;
  transaction_type: string;
  quantity: string;
  price: string;
  currency: string;
  fees: string;
  taxes: string;
  fx_rate: string;
  input_currency: string | null;
  input_price: string | null;
  input_fees: string | null;
  input_taxes: string | null;
  input_to_asset_rate: string | null;
  conversion_provider: string | null;
  conversion_effective_at: string | null;
  conversion_precision: string | null;
  broker: string;
  notes: string;
  external_id: string | null;
};
export type Position = {
  asset_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  sector: string | null;
  country: string | null;
  quantity: string;
  average_cost: string | null;
  current_price: string | null;
  cost_basis: string;
  current_value: string | null;
  unrealized_pl: string | null;
  realized_pl: string;
  dividends: string;
  weight: string | null;
  currency: string;
};
export type Snapshot = {
  date: string;
  base_currency: string;
  positions: Position[];
  total_value: string | null;
  positions_value: string | null;
  positions_pnl: string | null;
  positions_return_percent: string | null;
  cost_basis: string;
  cash: string | null;
  total_pl: string | null;
  return_percent: string | null;
  dividends: string;
  dividends_ytd: string;
  realized_pl: string;
  net_contributions: string;
  xirr: number | null;
  twr: string | null;
  complete: boolean;
  missing: string[];
  warnings: string[];
};

export type PortfolioChartPoint = {
  date: string;
  invested: string;
  value: string | null;
  pnl: string | null;
  realized: string;
  dividends: string;
  complete: boolean;
  missing: string[];
};
export type PortfolioCharts = {
  base_currency: string;
  selection: { asset_id: string; symbol: string; name: string }[];
  items: PortfolioChartPoint[];
  missing_days: number;
  method?: string;
};

export type TransactionFilters = {
  query: string;
  asset: string;
  type: string;
  currency: string;
  broker: string;
  from: string;
  to: string;
};

export const emptyTransactionFilters: TransactionFilters = {
  query: "",
  asset: "",
  type: "",
  currency: "",
  broker: "",
  from: "",
  to: "",
};

export function filterTransactions(
  items: Transaction[],
  assets: Asset[],
  filters: TransactionFilters,
) {
  const assetsById = new Map(assets.map((asset) => [asset.id, asset]));
  const query = filters.query.trim().toLocaleLowerCase("es");
  return items.filter((transaction) => {
    const asset = transaction.asset_id
      ? assetsById.get(transaction.asset_id)
      : undefined;
    const searchable = [
      transaction.date,
      transaction.transaction_type,
      transaction.quantity,
      transaction.price,
      transaction.currency,
      transaction.fees,
      transaction.taxes,
      transaction.broker,
      transaction.notes,
      transaction.external_id,
      transaction.input_currency,
      transaction.input_price,
      transaction.conversion_provider,
      transaction.conversion_precision,
      asset?.symbol,
      asset?.name,
    ]
      .join(" ")
      .toLocaleLowerCase("es");
    return (
      (!query || searchable.includes(query)) &&
      (!filters.asset || transaction.asset_id === filters.asset) &&
      (!filters.type || transaction.transaction_type === filters.type) &&
      (!filters.currency || transaction.currency === filters.currency) &&
      (!filters.broker || transaction.broker === filters.broker) &&
      (!filters.from || transaction.date >= filters.from) &&
      (!filters.to || transaction.date <= filters.to)
    );
  });
}

function chartPrices(
  items: PortfolioChartPoint[],
  field: "value" | "pnl",
): Price[] {
  return items.flatMap((item) => {
    const value = item[field];
    return value == null
      ? []
      : [
          {
            date: item.date,
            open: null,
            high: null,
            low: null,
            close: value,
            volume: null,
            provider: "portfolio-ledger",
            retrieved_at: "",
            adjustment: "ledger",
          },
        ];
  });
}

export function PortfolioSummary({ data }: { data: Snapshot }) {
  return (
    <>
      <div className="metrics">
        <Metric
          label="Valor actual de posiciones"
          value={money(data.positions_value, data.base_currency)}
          hint="Suma de todas las posiciones a precio actual"
        />
        <Metric
          label="Coste de posiciones"
          value={money(data.cost_basis, data.base_currency)}
          hint="Coste medio ponderado"
        />
        <Metric
          label="P/L acumulado"
          value={money(data.positions_pnl, data.base_currency)}
          hint="Latente + realizado + dividendos"
        />
        <Metric
          label="Rentabilidad sobre coste"
          value={
            data.positions_return_percent == null
              ? "No disponible"
              : `${number(data.positions_return_percent)}%`
          }
        />
      </div>
      {data.missing.length > 0 && (
        <div className="notice">
          Valoración incompleta: {data.missing.join(" · ")}
        </div>
      )}
      {data.warnings.map((w) => (
        <p className="muted" key={w}>
          {w}
        </p>
      ))}
    </>
  );
}

export function TransactionForm({
  assets,
  currency,
  initial,
  onSave,
  onCancel,
}: {
  assets: Asset[];
  currency: string;
  initial?: Transaction;
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [kind, setKind] = useState(initial?.transaction_type ?? "BUY");
  const [selectedAssetId, setSelectedAssetId] = useState(
    initial?.asset_id ?? assets[0]?.id ?? "",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const needsAsset = [
    "BUY",
    "SELL",
    "DIVIDEND",
    "SPLIT",
    "TRANSFER_IN",
    "TRANSFER_OUT",
  ].includes(kind);
  const selectedAsset = assets.find((asset) => asset.id === selectedAssetId);
  const executionDefault = initial?.executed_at
    ? (() => {
        const value = new Date(initial.executed_at);
        value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
        return value.toISOString().slice(0, 16);
      })()
    : initial?.date
      ? `${initial.date}T12:00`
      : (() => {
          const value = new Date();
          value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
          return value.toISOString().slice(0, 16);
        })();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const localExecution = String(values.executed_at);
    try {
      await onSave({
        ...values,
        date: localExecution.slice(0, 10),
        executed_at: new Date(localExecution).toISOString(),
        transaction_type: kind,
        asset_id: needsAsset ? values.asset_id : null,
        fx_rate: values.fx_rate || null,
        external_id: values.external_id || null,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>{initial ? "Editar transacción" : "Registrar transacción"}</h2>
      <p className="muted">
        Introduce precio y cargos en la moneda realmente utilizada. Si difiere
        de la moneda del activo, se convertirán al tipo histórico de la hora de
        ejecución; cuando el proveedor horario no esté disponible se utilizará
        el cambio diario oficial y quedará indicado en la transacción.
      </p>
      <ErrorNotice error={error} />
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
            Tipo de operación
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {[
                "BUY",
                "SELL",
                "DIVIDEND",
                "FEE",
                "DEPOSIT",
                "WITHDRAWAL",
                "SPLIT",
                "TRANSFER_IN",
                "TRANSFER_OUT",
                "INTEREST",
              ].map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          {needsAsset && (
            <label>
              Activo
              <select
                name="asset_id"
                value={selectedAssetId}
                onChange={(event) => setSelectedAssetId(event.target.value)}
                required
              >
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.symbol} · {a.exchange} · {a.currency}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Fecha y hora de ejecución
            <input
              type="datetime-local"
              name="executed_at"
              max={new Date().toISOString().slice(0, 16)}
              defaultValue={executionDefault}
              required
            />
          </label>
          <label>
            {kind === "SPLIT" ? "Factor new/old" : "Cantidad"}
            <input
              name="quantity"
              type="number"
              min="0.000000000001"
              step="any"
              defaultValue={initial?.quantity ?? "1"}
              required
            />
          </label>
          <label>
            Precio / importe bruto
            <input
              name="price"
              type="number"
              min="0"
              step="any"
              defaultValue={initial?.input_price ?? initial?.price ?? "0"}
              required
            />
          </label>
          <label>
            Moneda introducida / de pago
            <input
              name="currency"
              maxLength={3}
              defaultValue={initial?.input_currency ?? currency}
              required
            />
            {selectedAsset && (
              <small>Moneda del activo: {selectedAsset.currency}</small>
            )}
          </label>
          <label>
            Comisiones
            <input
              name="fees"
              type="number"
              min="0"
              step="any"
              defaultValue={initial?.input_fees ?? initial?.fees ?? "0"}
              required
            />
          </label>
          <label>
            Impuestos / retención
            <input
              name="taxes"
              type="number"
              min="0"
              step="any"
              defaultValue={initial?.input_taxes ?? initial?.taxes ?? "0"}
              required
            />
          </label>
          <label>
            FX moneda introducida → activo (opcional)
            <input
              name="input_to_asset_rate"
              type="number"
              min="0.000000000001"
              step="any"
              defaultValue={
                initial?.conversion_provider === "manual"
                  ? (initial.input_to_asset_rate ?? "")
                  : ""
              }
              placeholder="Automático"
            />
          </label>
          <label>
            FX activo → {currency} (opcional)
            <input
              name="fx_rate"
              type="number"
              min="0.000000000001"
              step="any"
              defaultValue={initial?.fx_rate}
            />
          </label>
          <label>
            Broker
            <input name="broker" defaultValue={initial?.broker} />
          </label>
          <label>
            ID externo (opcional)
            <input
              name="external_id"
              defaultValue={initial?.external_id ?? ""}
            />
          </label>
          <label>
            Notas
            <input name="notes" defaultValue={initial?.notes} />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary" disabled={busy}>
            {busy ? "Guardando…" : "Guardar transacción"}
          </button>
          <button type="button" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </form>
    </section>
  );
}

export function Portfolio({
  displayCurrency = "EUR",
}: {
  displayCurrency?: DisplayCurrency;
}) {
  const portfolios = useResource<PortfolioInfo[]>("/portfolios");
  const assets = useResource<Asset[]>("/assets");
  const [selected, setSelected] = useState("");
  const [chartAssetIds, setChartAssetIds] = useState<string[]>([]);
  const [chartDays, setChartDays] = useState(365);
  const current =
    portfolios.data?.find((p) => p.id === selected) ?? portfolios.data?.[0];
  const snapshot = useResource<Snapshot>(
    current
      ? `/portfolios/${current.id}/positions?display_currency=${displayCurrency}`
      : null,
  );
  const transactions = useResource<Transaction[]>(
    current ? `/portfolios/${current.id}/transactions` : null,
  );
  const chartPath = useMemo(() => {
    if (!current) return null;
    const params = new URLSearchParams({
      days: String(chartDays),
      display_currency: displayCurrency,
    });
    chartAssetIds.forEach((assetId) => params.append("asset_ids", assetId));
    return `/portfolios/${current.id}/charts?${params}`;
  }, [current, chartAssetIds, chartDays, displayCurrency]);
  const history = useResource<PortfolioCharts>(chartPath);
  const [newPortfolio, setNewPortfolio] = useState(false);
  const [form, setForm] = useState(false);
  const [edit, setEdit] = useState<Transaction | undefined>();
  const [error, setError] = useState("");
  const [csv, setCsv] = useState("");
  const [csvFilename, setCsvFilename] = useState("");
  const [filters, setFilters] = useState<TransactionFilters>(
    emptyTransactionFilters,
  );
  const [preview, setPreview] = useState<{
    rows: { row: number; valid: boolean; skipped?: boolean; error?: string }[];
    valid: boolean;
    imported: number;
  } | null>(null);
  const filtered = useMemo(
    () =>
      filterTransactions(transactions.data ?? [], assets.data ?? [], filters),
    [transactions.data, assets.data, filters],
  );
  const valueHistory = useMemo(
    () => chartPrices(history.data?.items ?? [], "value"),
    [history.data],
  );
  const pnlHistory = useMemo(
    () => chartPrices(history.data?.items ?? [], "pnl"),
    [history.data],
  );
  const investedHistory = useMemo(
    () =>
      (history.data?.items ?? []).flatMap((item) =>
        item.value == null
          ? []
          : [{ time: item.date, value: Number(item.invested) }],
      ),
    [history.data],
  );
  const types = [
    ...new Set((transactions.data ?? []).map((t) => t.transaction_type)),
  ].sort();
  const currencies = [
    ...new Set((transactions.data ?? []).map((t) => t.currency)),
  ].sort();
  const brokers = [
    ...new Set((transactions.data ?? []).map((t) => t.broker).filter(Boolean)),
  ].sort();
  function updateFilter(field: keyof TransactionFilters, value: string) {
    setFilters((old) => ({ ...old, [field]: value }));
  }
  function toggleChartAsset(assetId: string) {
    setChartAssetIds((selectedAssets) =>
      selectedAssets.includes(assetId)
        ? selectedAssets.filter((id) => id !== assetId)
        : [...selectedAssets, assetId],
    );
  }
  async function save(data: Record<string, unknown>) {
    if (!current) return;
    if (edit)
      await put(`/portfolios/${current.id}/transactions/${edit.id}`, data);
    else await post(`/portfolios/${current.id}/transactions`, data);
    setForm(false);
    setEdit(undefined);
    transactions.reload();
    snapshot.reload();
    history.reload();
  }
  async function remove(id: string) {
    if (
      !current ||
      !window.confirm(
        "¿Eliminar esta transacción? Se recalculará todo el historial.",
      )
    )
      return;
    try {
      await api(`/portfolios/${current.id}/transactions/${id}`, {
        method: "DELETE",
      });
      transactions.reload();
      snapshot.reload();
      history.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function importCSV(confirm: boolean) {
    if (!current) return;
    setError("");
    try {
      const r = await post<NonNullable<typeof preview>>(
        `/portfolios/${current.id}/import`,
        { content: csv, filename: csvFilename, confirm },
      );
      setPreview(r);
      if (confirm) {
        transactions.reload();
        snapshot.reload();
        history.reload();
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader eyebrow="TU PATRIMONIO" title="Portfolio">
        <button onClick={() => setNewPortfolio(!newPortfolio)}>
          Nueva cartera
        </button>
        {current && (
          <button
            className="primary"
            onClick={() => {
              setEdit(undefined);
              setForm(true);
            }}
          >
            Registrar transacción
          </button>
        )}
      </PageHeader>
      <ErrorNotice
        error={
          error ||
          portfolios.error ||
          snapshot.error ||
          transactions.error ||
          history.error
        }
      />
      {(newPortfolio || !portfolios.data?.length) && (
        <section className="panel">
          <h2>Crea una cartera</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const p = await post<PortfolioInfo>(
                  "/portfolios",
                  Object.fromEntries(new FormData(e.currentTarget)),
                );
                setSelected(p.id);
                setNewPortfolio(false);
                portfolios.reload();
              } catch (err) {
                setError((err as Error).message);
              }
            }}
          >
            <div className="form-grid">
              <label>
                Nombre de cartera
                <input
                  name="name"
                  placeholder="Core Portfolio"
                  maxLength={128}
                  required
                />
              </label>
              <label>
                Moneda base
                <input
                  name="base_currency"
                  defaultValue="EUR"
                  maxLength={3}
                  required
                />
              </label>
              <label>
                Descripción
                <input name="description" />
              </label>
            </div>
            <button className="primary">Crear cartera</button>
          </form>
        </section>
      )}
      <div className="tabs">
        {portfolios.data?.map((p) => (
          <button
            key={p.id}
            className={current?.id === p.id ? "selected" : ""}
            onClick={() => {
              setSelected(p.id);
              setForm(false);
              setEdit(undefined);
              setPreview(null);
              setFilters(emptyTransactionFilters);
              setChartAssetIds([]);
            }}
          >
            {p.name} · {p.base_currency}
          </button>
        ))}
      </div>
      {form && current && (
        <TransactionForm
          key={edit?.id ?? "new"}
          assets={assets.data ?? []}
          currency={current.base_currency}
          initial={edit}
          onSave={save}
          onCancel={() => setForm(false)}
        />
      )}
      {snapshot.loading ? (
        <Loading />
      ) : (
        snapshot.data && (
          <>
            <PortfolioSummary data={snapshot.data} />
            <section className="panel portfolio-history">
              <div className="panel-heading">
                <div>
                  <h2>Evolución del portfolio</h2>
                  <small>
                    {chartAssetIds.length
                      ? `${chartAssetIds.length} posiciones seleccionadas`
                      : "Portfolio global"}
                  </small>
                </div>
                <label className="range-control">
                  Periodo
                  <select
                    value={chartDays}
                    onChange={(event) =>
                      setChartDays(Number(event.target.value))
                    }
                  >
                    <option value={90}>3 meses</option>
                    <option value={365}>1 año</option>
                    <option value={1095}>3 años</option>
                    <option value={3653}>10 años</option>
                  </select>
                </label>
              </div>
              <p className="muted">
                Elige el conjunto que quieres agregar. Global incluye todas las
                posiciones con movimientos en la cartera.
              </p>
              <div className="position-picker">
                <button
                  className={chartAssetIds.length === 0 ? "selected" : ""}
                  onClick={() => setChartAssetIds([])}
                >
                  Global
                </button>
                {snapshot.data.positions.map((position) => (
                  <button
                    key={position.asset_id}
                    className={
                      chartAssetIds.includes(position.asset_id)
                        ? "selected"
                        : ""
                    }
                    onClick={() => toggleChartAsset(position.asset_id)}
                  >
                    {position.symbol}
                  </button>
                ))}
              </div>
              {history.loading ? (
                <Loading />
              ) : valueHistory.length ? (
                <>
                  {history.data?.missing_days ? (
                    <div className="notice">
                      Se han omitido {history.data.missing_days} días sin precio
                      histórico o tipo de cambio verificable.
                    </div>
                  ) : null}
                  <div className="portfolio-chart-grid">
                    <div>
                      <h3>Aportado frente a valor</h3>
                      <PriceChart
                        prices={valueHistory}
                        overlays={[
                          {
                            name: "Invertido",
                            color: "#8e98aa",
                            points: investedHistory,
                          },
                        ]}
                        height={320}
                        axisLabel={`Valor en ${history.data?.base_currency ?? snapshot.data.base_currency}`}
                        seriesLabel="Valor de posiciones"
                        unit={
                          history.data?.base_currency ??
                          snapshot.data.base_currency
                        }
                        valueFormat="compact"
                      />
                    </div>
                    <div>
                      <h3>P/L agregado diario</h3>
                      <PriceChart
                        prices={pnlHistory}
                        height={320}
                        axisLabel={`P/L en ${history.data?.base_currency ?? snapshot.data.base_currency}`}
                        seriesLabel="P/L total"
                        unit={
                          history.data?.base_currency ??
                          snapshot.data.base_currency
                        }
                        valueFormat="compact"
                      />
                    </div>
                  </div>
                  {history.data?.method && (
                    <p className="muted chart-method">{history.data.method}</p>
                  )}
                </>
              ) : (
                <Empty title="No hay precios históricos verificables para esta selección" />
              )}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Posiciones</h2>
                <Link to="/assets">Añadir activos →</Link>
              </div>
              {snapshot.data.positions.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "ACTIVO",
                          "CANTIDAD",
                          "PRECIO MEDIO",
                          "PRECIO ACTUAL",
                          "COSTE BASE",
                          "VALOR BASE",
                          "P/L LATENTE",
                          "P/L REALIZADO",
                          "DIVIDENDOS",
                          "PESO",
                        ].map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.data.positions.map((p) => (
                        <tr key={p.asset_id}>
                          <td>
                            <Link to={`/asset/${p.asset_id}`}>
                              <strong>{p.symbol}</strong>
                              <small>{p.name}</small>
                            </Link>
                          </td>
                          <td>{number(p.quantity, 8)}</td>
                          <td>{money(p.average_cost, p.currency)}</td>
                          <td>{money(p.current_price, p.currency)}</td>
                          <td>{money(p.cost_basis, current?.base_currency)}</td>
                          <td>
                            {money(p.current_value, current?.base_currency)}
                          </td>
                          <td>
                            {money(p.unrealized_pl, current?.base_currency)}
                          </td>
                          <td>
                            {money(p.realized_pl, current?.base_currency)}
                          </td>
                          <td>{money(p.dividends, current?.base_currency)}</td>
                          <td>
                            {p.weight == null ? "—" : `${number(p.weight)}%`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty title="Todavía no tienes posiciones">
                  <p>Añade activos y registra tu primera compra.</p>
                </Empty>
              )}
            </section>
            <div className="metrics">
              <Metric
                label="Dividendos netos"
                value={money(snapshot.data.dividends, current?.base_currency)}
              />
              <Metric
                label="Dividendos YTD"
                value={money(
                  snapshot.data.dividends_ytd,
                  current?.base_currency,
                )}
              />
              <Metric
                label="P/L realizado"
                value={money(snapshot.data.realized_pl, current?.base_currency)}
              />
              <Metric
                label="XIRR anualizado"
                value={
                  snapshot.data.xirr == null
                    ? "No disponible"
                    : `${number(snapshot.data.xirr * 100)}%`
                }
              />
            </div>
          </>
        )
      )}
      {current && (
        <>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Libro de transacciones</h2>
                <small>
                  {filtered.length} de {transactions.data?.length ?? 0}{" "}
                  movimientos
                </small>
              </div>
              <div className="actions">
                <a href={`/api/portfolios/${current.id}/export`}>
                  Exportar CSV
                </a>
                <a href={`/api/portfolios/${current.id}/export?format=json`}>
                  JSON
                </a>
              </div>
            </div>
            <div className="form-grid transaction-filters">
              <label>
                Buscar en todos los campos
                <input
                  value={filters.query}
                  onChange={(e) => updateFilter("query", e.target.value)}
                  placeholder="Ticker, notas, broker, importe…"
                />
              </label>
              <label>
                Activo
                <select
                  value={filters.asset}
                  onChange={(e) => updateFilter("asset", e.target.value)}
                >
                  <option value="">Todos</option>
                  {(assets.data ?? []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.symbol} · {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Tipo
                <select
                  value={filters.type}
                  onChange={(e) => updateFilter("type", e.target.value)}
                >
                  <option value="">Todos</option>
                  {types.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
                </select>
              </label>
              <label>
                Moneda
                <select
                  value={filters.currency}
                  onChange={(e) => updateFilter("currency", e.target.value)}
                >
                  <option value="">Todas</option>
                  {currencies.map((currency) => (
                    <option key={currency}>{currency}</option>
                  ))}
                </select>
              </label>
              <label>
                Broker
                <select
                  value={filters.broker}
                  onChange={(e) => updateFilter("broker", e.target.value)}
                >
                  <option value="">Todos</option>
                  {brokers.map((broker) => (
                    <option key={broker}>{broker}</option>
                  ))}
                </select>
              </label>
              <label>
                Desde
                <input
                  type="date"
                  value={filters.from}
                  onChange={(e) => updateFilter("from", e.target.value)}
                />
              </label>
              <label>
                Hasta
                <input
                  type="date"
                  value={filters.to}
                  onChange={(e) => updateFilter("to", e.target.value)}
                />
              </label>
              <div className="filter-actions">
                <button
                  onClick={() => setFilters(emptyTransactionFilters)}
                  disabled={!Object.values(filters).some(Boolean)}
                >
                  Limpiar filtros
                </button>
              </div>
            </div>
            {transactions.data?.length ? (
              filtered.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>FECHA</th>
                        <th>TIPO</th>
                        <th>ACTIVO</th>
                        <th>CANTIDAD</th>
                        <th>PRECIO / IMPORTE</th>
                        <th>MONEDA</th>
                        <th>CARGOS</th>
                        <th>BROKER</th>
                        <th>CONVERSIÓN</th>
                        <th>NOTAS</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((t) => (
                        <tr key={t.id}>
                          <td>{t.date}</td>
                          <td>
                            <span className="badge">{t.transaction_type}</span>
                          </td>
                          <td>
                            {assets.data?.find((a) => a.id === t.asset_id)
                              ?.symbol ?? "Efectivo"}
                          </td>
                          <td>{number(t.quantity, 8)}</td>
                          <td>{money(t.price, t.currency)}</td>
                          <td>{t.currency}</td>
                          <td>
                            {money(
                              Number(t.fees) + Number(t.taxes),
                              t.currency,
                            )}
                          </td>
                          <td>{t.broker || "—"}</td>
                          <td>
                            {t.input_currency &&
                            t.input_currency !== t.currency ? (
                              <>
                                {t.input_currency} → {t.currency}
                                <small>
                                  {t.input_to_asset_rate} ·{" "}
                                  {t.conversion_precision}
                                </small>
                              </>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>
                            <span title={t.notes}>{t.notes || "—"}</span>
                          </td>
                          <td>
                            <button
                              onClick={() => {
                                setEdit(t);
                                setForm(true);
                              }}
                            >
                              Editar
                            </button>{" "}
                            <button onClick={() => remove(t.id)}>
                              Eliminar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty title="No hay transacciones que coincidan con los filtros" />
              )
            ) : (
              <Empty title="Sin transacciones" />
            )}
          </section>
          <div className="two-col">
            <section className="panel">
              <h2>Importar CSV</h2>
              <p className="muted">
                Admite el CSV estándar y el historial de órdenes de MyInvestor.
                Las órdenes no finalizadas se omiten. Registra los activos antes
                de importar; máximo 1000 filas.
              </p>
              <label>
                Archivo CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setCsv(await file.text());
                      setCsvFilename(file.name);
                      setPreview(null);
                    }
                  }}
                />
              </label>
              <button disabled={!csv} onClick={() => importCSV(false)}>
                Vista previa
              </button>
              {preview && (
                <>
                  <p>
                    {preview.rows.length} filas ·{" "}
                    {preview.imported
                      ? `${preview.imported} importadas`
                      : preview.valid
                        ? "Formato válido"
                        : "Hay errores"}
                  </p>
                  <ul>
                    {preview.rows.slice(0, 20).map((r) => (
                      <li key={r.row}>
                        Fila {r.row}:{" "}
                        {r.skipped
                          ? r.error
                          : r.valid
                            ? "Formato válido"
                            : r.error}
                      </li>
                    ))}
                  </ul>
                  {!preview.imported && (
                    <button
                      className="primary"
                      disabled={!preview.valid}
                      onClick={() => importCSV(true)}
                    >
                      Confirmar importación
                    </button>
                  )}
                </>
              )}
            </section>
            <section className="panel">
              <h2>Tipo de cambio manual</h2>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await post(
                      "/fx",
                      Object.fromEntries(new FormData(e.currentTarget)),
                    );
                    snapshot.reload();
                  } catch (err) {
                    setError((err as Error).message);
                  }
                }}
              >
                <div className="form-grid">
                  <label>
                    Desde
                    <input
                      name="base"
                      defaultValue="USD"
                      required
                      maxLength={3}
                    />
                  </label>
                  <label>
                    A
                    <input
                      name="quote"
                      defaultValue={current.base_currency}
                      required
                      maxLength={3}
                    />
                  </label>
                  <label>
                    Fecha
                    <input
                      type="date"
                      name="date"
                      defaultValue={new Date().toISOString().slice(0, 10)}
                      required
                    />
                  </label>
                  <label>
                    Tipo
                    <input
                      type="number"
                      name="rate"
                      step="any"
                      min="0.000000000001"
                      required
                    />
                  </label>
                </div>
                <button>Guardar FX</button>
              </form>
            </section>
          </div>
        </>
      )}
    </>
  );
}
