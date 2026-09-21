import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "./Dashboard";

test("dashboard loads the created portfolio and its current snapshot", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const body = url.endsWith("/portfolios")
      ? [{ id: "portfolio-1", name: "Core Portfolio", base_currency: "EUR" }]
      : {
          date: "2026-09-20",
          base_currency: "EUR",
          positions: [
            {
              asset_id: "asset-1",
              symbol: "WORLD",
              name: "World Index Fund",
              asset_type: "MUTUAL_FUND",
              sector: null,
              country: null,
              quantity: "10",
              average_cost: "11",
              current_price: "12",
              cost_basis: "110",
              current_value: "120",
              unrealized_pl: "10",
              realized_pl: "0",
              dividends: "0",
              weight: "100",
              currency: "EUR",
            },
          ],
          total_value: "10",
          positions_value: "120",
          positions_pnl: "10",
          positions_return_percent: "9.09",
          cost_basis: "110",
          cash: "-110",
          total_pl: null,
          return_percent: null,
          dividends: "0",
          dividends_ytd: "0",
          realized_pl: "0",
          net_contributions: "0",
          xirr: null,
          twr: null,
          complete: true,
          missing: [],
      warnings: ["Aportaciones de efectivo no registradas"],
        };
    return { ok: true, json: async () => body } as Response;
  });

  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

  expect(
    await screen.findByRole("button", { name: "Core Portfolio · EUR" }),
  ).toBeVisible();
  expect(await screen.findByText("World Index Fund")).toBeVisible();
  expect(screen.getAllByText(/120,00/)).toHaveLength(2);
  expect(screen.queryByText(/-110,00/)).not.toBeInTheDocument();
  expect(
    screen.queryByText("Crea una cartera para empezar"),
  ).not.toBeInTheDocument();
});
