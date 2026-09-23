import type { ReactNode } from 'react';
import { Inbox, LoaderCircle } from 'lucide-react';

export function Loading() { return <div className="state" role="status"><LoaderCircle className="spin" size={22} /> Cargando…</div>; }
export function ErrorNotice({ error }: { error: string }) { return error ? <div role="alert" className="notice error">{error}</div> : null; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="state empty"><Inbox size={30} /><h3>{title}</h3><div>{children}</div></div>; }
export function Metric({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'positive' | 'negative' }) { return <article className={`metric${value.length > 14 ? " metric-wide" : ""}`}><span>{label}</span><strong className={tone}>{value}</strong>{hint && <small>{hint}</small>}</article>; }
export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) { return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div><div className="actions">{children}</div></div>; }
export function money(value: string | number | null | undefined, currency = 'EUR'): string { return value == null ? 'No disponible' : new Intl.NumberFormat('es-ES', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value)); }
export function number(value: string | number | null | undefined, digits = 2): string { return value == null ? 'No disponible' : new Intl.NumberFormat('es-ES', { maximumFractionDigits: digits }).format(Number(value)); }

export function compactNumber(value: string | number | null | undefined, digits = 2): string {
  if (value == null) return 'No disponible';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 'No disponible';
  const absolute = Math.abs(numeric);
  const scales = [
    { threshold: 1e12, divisor: 1e12, suffix: 'T' },
    { threshold: 1e9, divisor: 1e9, suffix: 'B' },
    { threshold: 1e6, divisor: 1e6, suffix: 'M' },
    { threshold: 1e3, divisor: 1e3, suffix: 'mil' },
  ];
  const scale = scales.find(item => absolute >= item.threshold);
  if (!scale) return number(numeric, absolute > 0 && absolute < 0.01 ? 8 : digits);
  return `${number(numeric / scale.divisor, digits)} ${scale.suffix}`;
}
