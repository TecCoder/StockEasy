export type User = { id: string; username: string; csrf_token: string };
export type Preferences = { theme: "dark" | "light"; base_currency: string };
export type DisplayCurrency = "EUR" | "USD";
export type Asset = {
  id: string;
  symbol: string;
  name: string;
  asset_type: string;
  exchange: string;
  currency: string;
  sector?: string;
  industry?: string;
  country?: string;
  cik?: string;
  provider?: string;
  provider_asset_id?: string;
};
export type Quote = {
  price: string | null;
  date: string | null;
  currency: string;
  provider: string | null;
  retrieved_at: string | null;
  change_percent?: number;
  market_cap?: number;
  stale: boolean;
  warning?: string;
};
export type Price = {
  date: string;
  time?: number;
  open: string | null;
  high: string | null;
  low: string | null;
  close: string;
  volume: string | null;
  provider: string;
  retrieved_at: string;
  adjustment: string;
};
export type History = {
  items: Price[];
  warning?: string;
  stale: boolean;
  coverage_start: string | null;
  coverage_end: string | null;
};
export type ValuationPoint = {
  date: string;
  price: string;
  eps_ttm: string;
  pe: string;
  eps_periods: {
    start: string;
    end: string;
    filed: string;
    accession: string;
  }[];
};
export type Valuation = {
  current_pe: string | null;
  ttm_eps: string | null;
  price_date: string | null;
  historical_pe?: ValuationPoint[];
  sector_pe: number | null;
  warning: string;
  statistics?: {
    median: number | null;
    mean: number | null;
    p25: number | null;
    p75: number | null;
    percentile: number | null;
  };
};
export type Watchlist = { id: string; name: string; comment: string };
