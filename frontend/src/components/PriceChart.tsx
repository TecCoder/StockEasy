import { useEffect, useRef, type CSSProperties } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  type ISeriesApi,
  LineSeries,
  type SeriesType,
  type Time,
} from "lightweight-charts";
import type { Price } from "../types";

export type Series = {
  name: string;
  color: string;
  points: { time: string; value: number }[];
};
export type ChartValueFormat = "price" | "compact" | "percent" | "number";
const EMPTY_OVERLAYS: Series[] = [];

function chartValue(
  value: number,
  format: ChartValueFormat,
  unit: string,
): string {
  if (format === "percent") {
    return `${new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 }).format(value * 100)} %`;
  }
  if (format === "compact") {
    const absolute = Math.abs(value);
    const scale: [number, string] =
      absolute >= 1e12
        ? [1e12, "T"]
        : absolute >= 1e9
          ? [1e9, "B"]
          : absolute >= 1e6
            ? [1e6, "M"]
            : absolute >= 1e3
              ? [1e3, "mil"]
              : [1, ""];
    const formatted = new Intl.NumberFormat("es-ES", {
      maximumFractionDigits: 2,
    }).format(value / scale[0]);
    return `${formatted}${scale[1] ? ` ${scale[1]}` : ""}${unit ? ` ${unit}` : ""}`;
  }
  const maximumFractionDigits =
    format === "price" && Math.abs(value) < 0.01 ? 8 : 2;
  const formatted = new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
  }).format(value);
  return `${formatted}${unit ? ` ${unit}` : ""}`;
}

function exactChartValue(
  value: number,
  format: ChartValueFormat,
  unit: string,
): string {
  const normalized = format === "percent" ? value * 100 : value;
  const maximumFractionDigits =
    format === "price" && Math.abs(value) < 0.01
      ? 8
      : format === "percent"
        ? 4
        : 4;
  const formatted = new Intl.NumberFormat("es-ES", {
    maximumFractionDigits,
  }).format(normalized);
  return `${formatted}${format === "percent" ? " %" : unit ? ` ${unit}` : ""}`;
}

function displayedTime(time: Time | undefined): string {
  if (time == null) return "";
  if (typeof time === "string")
    return new Intl.DateTimeFormat("es-ES").format(
      new Date(`${time}T00:00:00`),
    );
  if (typeof time === "number")
    return new Intl.DateTimeFormat("es-ES", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(time * 1000));
  return `${String(time.day).padStart(2, "0")}/${String(time.month).padStart(2, "0")}/${time.year}`;
}

function valueFromPoint(point: unknown): number | null {
  if (!point || typeof point !== "object") return null;
  if ("value" in point && typeof point.value === "number") return point.value;
  if ("close" in point && typeof point.close === "number") return point.close;
  return null;
}

type Props = {
  prices: Price[];
  overlays?: Series[];
  height?: number;
  axisLabel?: string;
  seriesLabel?: string;
  unit?: string;
  valueFormat?: ChartValueFormat;
};

export function PriceChart({
  prices,
  overlays = EMPTY_OVERLAYS,
  height = 380,
  axisLabel = "Valor",
  seriesLabel = "Precio",
  unit = "",
  valueFormat = "price",
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!container.current) return;
    const light = document.documentElement.dataset.theme === "light";
    const element = container.current;
    let compact = element.clientWidth < 500;
    const formatter = (value: number) =>
      chartValue(value, valueFormat, compact ? "" : unit);
    const priceFormat = {
      type: "custom" as const,
      formatter,
      minMove: valueFormat === "price" ? 0.00000001 : 0.01,
    };
    const chart = createChart(container.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: light ? "#647184" : "#8e98aa",
        fontFamily: "Segoe UI",
        fontSize: compact ? 11 : 12,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: light ? "#edf1f5" : "#202733" },
        horzLines: { color: light ? "#edf1f5" : "#202733" },
      },
      rightPriceScale: {
        borderVisible: false,
        minimumWidth: compact ? 64 : 96,
      },
      timeScale: { borderVisible: false, minBarSpacing: 0.001 },
      handleScroll: { vertTouchDrag: false },
      crosshair: { mode: 0 },
    });
    const tooltipSeries: { series: ISeriesApi<SeriesType>; name: string }[] =
      [];
    if (
      prices.every((p) => p.open != null && p.high != null && p.low != null)
    ) {
      const candles = chart.addSeries(CandlestickSeries, {
        title: compact ? "" : seriesLabel,
        priceFormat,
        upColor: "#b5ef76",
        downColor: "#f78e99",
        borderVisible: false,
        wickUpColor: "#b5ef76",
        wickDownColor: "#f78e99",
      });
      tooltipSeries.push({
        series: candles as ISeriesApi<SeriesType>,
        name: seriesLabel,
      });
      candles.setData(
        prices.map((p) => ({
          time: (p.time ?? p.date) as Time,
          open: Number(p.open),
          high: Number(p.high),
          low: Number(p.low),
          close: Number(p.close),
        })),
      );
    } else {
      const line = chart.addSeries(LineSeries, {
        title: compact ? "" : seriesLabel,
        priceFormat,
        color: "#b5ef76",
        lineWidth: 2,
      });
      tooltipSeries.push({
        series: line as ISeriesApi<SeriesType>,
        name: seriesLabel,
      });
      line.setData(
        prices.map((p) => ({
          time: (p.time ?? p.date) as Time,
          value: Number(p.close),
        })),
      );
    }
    const volumes = prices.filter((p) => p.volume != null);
    if (volumes.length) {
      const volume = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
        color: "#405c39",
      });
      volume
        .priceScale()
        .applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } });
      volume.setData(
        volumes.map((p) => ({
          time: (p.time ?? p.date) as Time,
          value: Number(p.volume),
        })),
      );
    }
    overlays.forEach((overlay) => {
      const series = chart.addSeries(LineSeries, {
        color: overlay.color,
        lineWidth: 1,
        title: compact ? "" : overlay.name,
        priceLineVisible: false,
        priceFormat,
      });
      tooltipSeries.push({
        series: series as ISeriesApi<SeriesType>,
        name: overlay.name,
      });
      series.setData(
        overlay.points.map((point) => ({
          time: point.time as Time,
          value: point.value,
        })),
      );
    });
    chart.subscribeCrosshairMove((param) => {
      if (
        !tooltip.current ||
        !container.current ||
        !param.point ||
        !param.time
      ) {
        if (tooltip.current) tooltip.current.hidden = true;
        return;
      }
      const values = tooltipSeries.flatMap((item) => {
        const value = valueFromPoint(param.seriesData.get(item.series));
        return value == null
          ? []
          : [`${item.name}: ${exactChartValue(value, valueFormat, unit)}`];
      });
      if (!values.length) {
        tooltip.current.hidden = true;
        return;
      }
      tooltip.current.textContent = [displayedTime(param.time), ...values].join(
        "\n",
      );
      tooltip.current.hidden = false;
      const tooltipWidth = tooltip.current.offsetWidth;
      const left =
        param.point.x > container.current.clientWidth - tooltipWidth
          ? param.point.x - tooltipWidth - 12
          : param.point.x + 12;
      tooltip.current.style.left = `${Math.max(8, Math.min(left, container.current.clientWidth - tooltipWidth - 8))}px`;
      tooltip.current.style.top = `${Math.max(8, Math.min(param.point.y - 36, container.current.clientHeight - tooltip.current.offsetHeight - 8))}px`;
    });
    chart.timeScale().fitContent();
    const observer = new ResizeObserver(() => {
      const nextCompact = element.clientWidth < 500;
      if (nextCompact === compact) return;
      compact = nextCompact;
      chart.applyOptions({
        layout: { fontSize: compact ? 11 : 12 },
        rightPriceScale: { minimumWidth: compact ? 64 : 96 },
      });
      tooltipSeries.forEach(({ series, name }) => {
        series.applyOptions({ title: compact ? "" : name, priceFormat });
      });
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [prices, overlays, height, seriesLabel, unit, valueFormat]);

  const scaleHint = valueFormat === "compact" ? " · mil, M, B y T" : "";
  return (
    <div
      className="chart-shell"
      aria-label={`${seriesLabel}. Eje Y: ${axisLabel}. Eje X: fecha.`}
    >
      <div className="chart-axis-legend">
        <span>
          <strong>Eje Y</strong> · {axisLabel}
          {scaleHint}
        </span>
        <span>
          <strong>Eje X</strong> · Fecha
        </span>
      </div>
      <div className="chart-series-legend" aria-label="Series de la gráfica">
        <span>
          <i style={{ background: "#b5ef76" }} />
          {seriesLabel}
        </span>
        {overlays.map((overlay) => (
          <span key={overlay.name}>
            <i style={{ background: overlay.color }} />
            {overlay.name}
          </span>
        ))}
      </div>
      <div className="chart-plot">
        <div
          ref={container}
          className="chart-canvas"
          style={{ "--chart-height": `${height}px` } as CSSProperties}
        />
        <div ref={tooltip} className="chart-tooltip" hidden />
      </div>
    </div>
  );
}
