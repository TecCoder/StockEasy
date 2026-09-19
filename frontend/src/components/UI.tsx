import type { ReactNode } from 'react';
import { Inbox, LoaderCircle } from 'lucide-react';

export function Loading() { return <div className="state" role="status"><LoaderCircle className="spin" size={22} /> Cargando…</div>; }
export function ErrorNotice({ error }: { error: string }) { return error ? <div role="alert" className="notice error">{error}</div> : null; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="state empty"><Inbox size={30} /><h3>{title}</h3><div>{children}</div></div>; }
export function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) { return <article className="metric"><span>{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</article>; }
export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) { return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div><div className="actions">{children}</div></div>; }
export function money(value: string | number | null | undefined, currency = 'EUR'): string { return value == null ? 'No disponible' : new Intl.NumberFormat('es-ES', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(value)); }
export function number(value: string | number | null | undefined, digits = 2): string { return value == null ? 'No disponible' : new Intl.NumberFormat('es-ES', { maximumFractionDigits: digits }).format(Number(value)); }
