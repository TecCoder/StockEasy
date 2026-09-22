import { useMemo, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw, Star } from "lucide-react";
import { api, post } from "../api/client";
import {
  Empty,
  ErrorNotice,
  Loading,
  Metric,
  PageHeader,
  money,
  number,
} from "../components/UI";
import { TechnicalAnalysis } from "../components/TechnicalAnalysis";
import { PriceChart } from "../components/PriceChart";
import {
  aggregatePrices,
  type CandleInterval,
} from "../components/priceAggregation";
import { useResource } from "../hooks/useResource";
import type { Asset, History, Quote, Valuation, Watchlist } from "../types";
import { Fundamentals } from "./Fundamentals";

export function AssetDetail() {
  const { id } = useParams();
  const asset = useResource<Asset>(`/assets/${id}`);
  const history = useResource<History>(`/assets/${id}/prices`);
  const quote = useResource<Quote>(`/assets/${id}/quote`);
  const valuation = useResource<Valuation>(
    asset.data?.asset_type === "STOCK" ? `/assets/${id}/valuation` : null,
  );
  const lists = useResource<Watchlist[]>("/watchlists");
  const [range, setRange] = useState("1Y");
  const [candleInterval, setCandleInterval] = useState<CandleInterval>("daily");
  const intraday = useResource<History>(
    candleInterval === "1h" || candleInterval === "4h"
      ? `/assets/${id}/intraday?interval=${candleInterval}`
      : null,
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const prices = useMemo(() => {
    const days = (
      {
        "1M": 31,
        "3M": 93,
        "6M": 186,
        "1Y": 366,
        "3Y": 1096,
        "5Y": 1827,
        "10Y": 3653,
      } as Record<string, number>
    )[range];
    const min =
      range === "YTD"
        ? `${new Date().getFullYear()}-01-01`
        : days
          ? new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)
          : "";
    return (history.data?.items ?? []).filter((p) => p.date >= min);
  }, [history.data, range]);
  const chartPrices = useMemo(
    () =>
      candleInterval === "1h" || candleInterval === "4h"
        ? (intraday.data?.items ?? [])
        : aggregatePrices(prices, candleInterval),
    [candleInterval, intraday.data, prices],
  );
  const intradaySelected = candleInterval === "1h" || candleInterval === "4h";
  async function refresh() {
    setRefreshing(true);
    setError("");
    try {
      if (intradaySelected)
        await api(
          `/assets/${id}/intraday?interval=${candleInterval}&refresh=true`,
        );
      else await api(`/assets/${id}/prices?refresh=true`);
      history.reload();
      intraday.reload();
      quote.reload();
      valuation.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  }
  async function nav(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await post(
        `/assets/${id}/prices`,
        Object.fromEntries(new FormData(event.currentTarget)),
      );
      history.reload();
      quote.reload();
      setNotice("Precio registrado");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (asset.loading) return <Loading />;
  if (!asset.data)
    return <ErrorNotice error={asset.error || "Activo no encontrado"} />;
  const a = asset.data;
  const dailyChange =
    quote.data?.change_percent == null
      ? null
      : Number(quote.data.change_percent);
  const changeTone =
    a.asset_type === "CRYPTO" && dailyChange != null && dailyChange !== 0
      ? dailyChange > 0
        ? ("positive" as const)
        : ("negative" as const)
      : undefined;
  const intervals: [CandleInterval, string][] =
    a.asset_type === "STOCK"
      ? [
          ["daily", "Día"],
          ["weekly", "Semana"],
          ["monthly", "Mes"],
          ["4h", "4 h"],
          ["1h", "1 h"],
        ]
      : [
          ["daily", "Día"],
          ["weekly", "Semana"],
          ["monthly", "Mes"],
        ];
  const chartLoading = intradaySelected ? intraday.loading : history.loading;
  const chartWarning = intradaySelected
    ? intraday.data?.warning
    : history.data?.warning;
  const coverageStart = intradaySelected
    ? intraday.data?.coverage_start
    : history.data?.coverage_start;
  const coverageEnd = intradaySelected
    ? intraday.data?.coverage_end
    : history.data?.coverage_end;
  return (
    <>
      <PageHeader
        eyebrow={`${a.asset_type} / ${a.exchange} / ${a.currency}`}
        title={`${a.symbol} · ${a.name}`}
      >
        <button disabled={refreshing} onClick={refresh}>
          <RefreshCw size={15} />
          Actualizar datos
        </button>
      </PageHeader>
      <ErrorNotice
        error={
          error ||
          history.error ||
          quote.error ||
          (a.asset_type === "STOCK" ? valuation.error : "")
        }
      />
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      <div className="metrics">
        <Metric
          label="Último precio"
          value={money(quote.data?.price, a.currency)}
          hint={quote.data?.date ?? "Sin cotización"}
        />
        <Metric
          label="Cambio diario"
          value={
            dailyChange == null ? "No disponible" : `${dailyChange.toFixed(2)}%`
          }
          tone={changeTone}
        />
        {a.asset_type === "STOCK" && (
          <Metric
            label="PER diario · TTM"
            value={number(valuation.data?.current_pe)}
            hint={valuation.data?.price_date ?? "Sin EPS TTM compatible"}
          />
        )}
        <Metric
          label="Capitalización"
          value={money(quote.data?.market_cap, a.currency)}
        />
        <Metric
          label="Fuente"
          value={quote.data?.provider ?? "No disponible"}
          hint={
            quote.data?.stale
              ? "Dato guardado · revisar fecha"
              : "Datos del proveedor"
          }
        />
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Histórico de precios</h2>
          <span className="badge">
            {intradaySelected ? `INTRADÍA · ${candleInterval}` : "EOD"}
          </span>
        </div>
        <div className="chart-controls">
          {!intradaySelected && (
            <div>
              <small>Rango</small>
              <div className="tabs">
                {["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y", "MAX"].map(
                  (value) => (
                    <button
                      key={value}
                      onClick={() => setRange(value)}
                      className={range === value ? "selected" : ""}
                    >
                      {value}
                    </button>
                  ),
                )}
              </div>
            </div>
          )}
          <div>
            <small>Temporalidad de vela</small>
            <div className="tabs">
              {intervals.map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setCandleInterval(value)}
                  className={candleInterval === value ? "selected" : ""}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
        {chartLoading ? (
          <Loading />
        ) : chartPrices.length ? (
          intradaySelected ? (
            <PriceChart
              prices={chartPrices}
              axisLabel={`Precio (${a.currency})`}
              seriesLabel={`Precio · ${candleInterval}`}
              unit={a.currency}
            />
          ) : (
            <TechnicalAnalysis
              assetId={a.id}
              prices={chartPrices}
              currency={a.currency}
            />
          )
        ) : (
          <Empty
            title={
              intradaySelected
                ? "Datos intradía no disponibles"
                : "Datos no disponibles"
            }
          >
            <p>{chartWarning ?? "No hay observaciones en este rango."}</p>
          </Empty>
        )}
        <small>
          Cobertura: {coverageStart ?? "—"} → {coverageEnd ?? "—"}.{" "}
          {chartPrices.length ? chartWarning : ""}
        </small>
      </section>
      <div className="two-col">
        <section className="panel">
          <h2>Registrar precio / NAV</h2>
          <form onSubmit={nav}>
            <div className="form-grid">
              <label>
                Fecha
                <input
                  type="date"
                  name="date"
                  required
                  max={new Date().toISOString().slice(0, 10)}
                  defaultValue={new Date().toISOString().slice(0, 10)}
                />
              </label>
              <label>
                Precio ({a.currency})
                <input type="number" name="close" step="any" min="0" required />
              </label>
            </div>
            <button>Guardar precio</button>
          </form>
        </section>
        <section className="panel">
          <h2>
            <Star size={16} /> Añadir a watchlist
          </h2>
          {lists.data?.length ? (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const listId = new FormData(e.currentTarget).get("watchlist");
                try {
                  await post(`/watchlists/${listId}/items`, { asset_id: id });
                  setNotice("Activo añadido a la watchlist");
                } catch (err) {
                  setError((err as Error).message);
                }
              }}
            >
              <label>
                Watchlist
                <select name="watchlist">
                  {lists.data.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </label>
              <button>Añadir a watchlist</button>
            </form>
          ) : (
            <p className="muted">Crea tu primera lista en Watchlists.</p>
          )}
        </section>
      </div>
      {a.asset_type === "STOCK" && (
        <Fundamentals
          assetId={a.id}
          valuation={valuation.data}
          valuationLoading={valuation.loading}
        />
      )}
    </>
  );
}
