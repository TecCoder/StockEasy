import { expect, test } from "vitest";
import type { Price } from "../types";
import { aggregatePrices } from "./priceAggregation";

const prices: Price[] = [
  {
    date: "2026-09-21",
    open: "10",
    high: "12",
    low: "9",
    close: "11",
    volume: "100",
    provider: "test",
    retrieved_at: "",
    adjustment: "raw",
  },
  {
    date: "2026-09-22",
    open: "11",
    high: "14",
    low: "10",
    close: "13",
    volume: "150",
    provider: "test",
    retrieved_at: "",
    adjustment: "raw",
  },
];

test("builds a weekly OHLC candle and adds volume", () => {
  expect(aggregatePrices(prices, "weekly")).toEqual([
    expect.objectContaining({
      date: "2026-09-22",
      open: "10",
      high: "14",
      low: "9",
      close: "13",
      volume: "250",
    }),
  ]);
});

test("keeps daily observations unchanged", () => {
  expect(aggregatePrices(prices, "daily")).toBe(prices);
});
