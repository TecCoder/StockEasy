import { useEffect, useRef } from 'react';
import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type Time } from 'lightweight-charts';
import type { Price } from '../types';

export type Series = { name: string; color: string; points: { time: string; value: number }[] };
export function PriceChart({ prices, overlays = [], height = 380 }: { prices: Price[]; overlays?: Series[]; height?: number }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!container.current) return;
    const light = document.documentElement.dataset.theme === 'light';
    const chart = createChart(container.current, { autoSize: true, height, layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: light ? '#647184' : '#8e98aa', fontFamily: 'Segoe UI', attributionLogo: true }, grid: { vertLines: { color: light ? '#edf1f5' : '#202733' }, horzLines: { color: light ? '#edf1f5' : '#202733' } }, rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false }, crosshair: { mode: 0 } });
    if (prices.every(p => p.open != null && p.high != null && p.low != null)) {
      const candles = chart.addSeries(CandlestickSeries, { upColor: '#b5ef76', downColor: '#f78e99', borderVisible: false, wickUpColor: '#b5ef76', wickDownColor: '#f78e99' });
      candles.setData(prices.map(p => ({ time: p.date as Time, open: Number(p.open), high: Number(p.high), low: Number(p.low), close: Number(p.close) })));
    } else {
      const line = chart.addSeries(LineSeries, { color: '#b5ef76', lineWidth: 2 });
      line.setData(prices.map(p => ({ time: p.date as Time, value: Number(p.close) })));
    }
    const volumes = prices.filter(p => p.volume != null);
    if (volumes.length) { const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume', color: '#405c39' }); volume.priceScale().applyOptions({ scaleMargins: { top: .86, bottom: 0 } }); volume.setData(volumes.map(p => ({ time: p.date as Time, value: Number(p.volume) }))); }
    overlays.forEach(o => { const series = chart.addSeries(LineSeries, { color: o.color, lineWidth: 1, title: o.name, priceLineVisible: false }); series.setData(o.points.map(p => ({ time: p.time as Time, value: p.value }))); });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [prices, overlays, height]);
  return <div ref={container} style={{ height, width: '100%' }} aria-label="Gráfico de precios con zoom y crosshair" />;
}
