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
export type Watchlist = { id: string; name: string; comment: string };
