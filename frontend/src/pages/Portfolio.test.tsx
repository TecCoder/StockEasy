import {
  emptyTransactionFilters,
  filterTransactions,
  type Transaction,
} from "./Portfolio";
import type { Asset } from "../types";

const assets: Asset[] = [
  {
    id: "world",
    symbol: "WORLD",
    name: "World Index Fund",
    asset_type: "MUTUAL_FUND",
    exchange: "EUFUND",
    currency: "EUR",
  },
  {
    id: "em",
    symbol: "EM",
    name: "Emerging Markets Fund",
    asset_type: "MUTUAL_FUND",
    exchange: "EUFUND",
    currency: "EUR",
  },
];

const transactions: Transaction[] = [
  {
    id: "one",
    asset_id: "world",
    date: "2025-01-10",
    transaction_type: "BUY",
    quantity: "10",
    price: "100",
    currency: "EUR",
    fees: "0",
    taxes: "0",
    fx_rate: "1",
    broker: "MyInvestor",
    notes: "Compra mensual",
    external_id: "order-1",
  },
  {
    id: "two",
    asset_id: "em",
    date: "2025-02-10",
    transaction_type: "SELL",
    quantity: "2",
    price: "120",
    currency: "EUR",
    fees: "1",
    taxes: "0",
    fx_rate: "1",
    broker: "Other",
    notes: "",
    external_id: "order-2",
  },
];

test("filters transactions across text, asset, type, broker and date", () => {
  expect(
    filterTransactions(transactions, assets, {
      ...emptyTransactionFilters,
      query: "world",
    }),
  ).toEqual([transactions[0]]);
  expect(
    filterTransactions(transactions, assets, {
      ...emptyTransactionFilters,
      asset: "em",
      type: "SELL",
    }),
  ).toEqual([transactions[1]]);
  expect(
    filterTransactions(transactions, assets, {
      ...emptyTransactionFilters,
      broker: "MyInvestor",
      from: "2025-01-01",
      to: "2025-01-31",
    }),
  ).toEqual([transactions[0]]);
  expect(
    filterTransactions(transactions, assets, {
      ...emptyTransactionFilters,
      from: "2025-03-01",
    }),
  ).toEqual([]);
});
