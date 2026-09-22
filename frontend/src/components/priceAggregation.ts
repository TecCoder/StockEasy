import type { Price } from "../types";

export type CandleInterval = "daily" | "weekly" | "monthly" | "1h" | "4h";

function bucket(date: string, interval: CandleInterval): string {
  if (interval === "monthly") return date.slice(0, 7);
  const value = new Date(`${date}T00:00:00Z`);
  const day = value.getUTCDay() || 7;
  value.setUTCDate(value.getUTCDate() - day + 1);
  return value.toISOString().slice(0, 10);
}

export function aggregatePrices(
  prices: Price[],
  interval: CandleInterval,
): Price[] {
  if (interval !== "weekly" && interval !== "monthly") return prices;
  const groups = new Map<string, Price[]>();
  for (const price of prices) {
    const key = bucket(price.date, interval);
    groups.set(key, [...(groups.get(key) ?? []), price]);
  }
  return [...groups.values()].map((group) => {
    const sorted = [...group].sort((left, right) =>
      left.date.localeCompare(right.date),
    );
    const first = sorted[0];
    const last = sorted.at(-1)!;
    const highs = sorted.map((value) => Number(value.high ?? value.close));
    const lows = sorted.map((value) => Number(value.low ?? value.close));
    const volumes = sorted.flatMap((value) =>
      value.volume == null ? [] : [Number(value.volume)],
    );
    return {
      ...last,
      open: first.open ?? first.close,
      high: String(Math.max(...highs)),
      low: String(Math.min(...lows)),
      volume: volumes.length
        ? String(volumes.reduce((total, value) => total + value, 0))
        : null,
      provider: sorted.every((value) => value.provider === first.provider)
        ? first.provider
        : "varios",
      adjustment: sorted.every((value) => value.adjustment === first.adjustment)
        ? first.adjustment
        : "mixed",
    };
  });
}
