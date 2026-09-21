from app.core.config import settings
from app.providers.base import ProviderError, ProviderResult
from app.providers.gateway import Gateway

# Ordered preferred standard concepts. Custom extensions are not guessed.
CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss"],
    "eps": ["EarningsPerShareDiluted"],
    "eps_basic": ["EarningsPerShareBasic"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "assets": ["Assets"],
    "equity": ["StockholdersEquity"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "inventory": ["InventoryNet"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["ShortTermBorrowings"],
    "current_debt": ["LongTermDebtCurrent"],
    "shares": ["CommonStockSharesOutstanding"],
    "sbc": ["ShareBasedCompensation"],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
}


class SEC:
    name = "sec"

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def request(self, url: str, refresh: bool = False) -> ProviderResult:
        if not settings.sec_user_agent or "@" not in settings.sec_user_agent:
            raise ProviderError("SEC: configura SEC_USER_AGENT con nombre y contacto real")
        return self.gateway.get(
            self.name,
            url,
            headers={"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"},
            ttl=settings.fundamental_ttl,
            refresh=refresh,
        )

    def resolve_cik(self, symbol: str) -> str:
        response = self.request("https://www.sec.gov/files/company_tickers.json")
        matches = [
            str(x["cik_str"]).zfill(10)
            for x in response.data.values()
            if x["ticker"].upper() == symbol.upper()
        ]
        if len(matches) != 1:
            raise ProviderError("SEC: CIK no disponible o ambiguo; indícalo manualmente")
        return matches[0]

    def search_companies(self, query: str) -> ProviderResult:
        """Search the SEC public company ticker catalogue and retain each CIK."""
        response = self.request("https://www.sec.gov/files/company_tickers_exchange.json")
        fields = response.data.get("fields", [])
        rows = response.data.get("data", [])
        required = {"cik", "name", "ticker", "exchange"}
        if not required.issubset(fields) or not isinstance(rows, list):
            raise ProviderError("SEC: catálogo de empresas con formato no reconocido")

        positions = {field: fields.index(field) for field in required}
        needle = query.strip().casefold()
        matches = []
        for row in rows:
            if not isinstance(row, list) or len(row) < len(fields):
                continue
            symbol = str(row[positions["ticker"]]).strip().upper()
            name = str(row[positions["name"]]).strip()
            if not symbol or not name:
                continue
            if needle not in symbol.casefold() and needle not in name.casefold():
                continue
            exchange = str(row[positions["exchange"]] or "SEC").strip().upper()
            cik = str(row[positions["cik"]]).zfill(10)
            matches.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "asset_type": "STOCK",
                    "exchange": exchange,
                    "currency": "USD",
                    "provider": self.name,
                    "provider_asset_id": cik,
                    "cik": cik,
                }
            )

        matches.sort(
            key=lambda item: (
                item["symbol"].casefold() != needle,
                not item["symbol"].casefold().startswith(needle),
                not item["name"].casefold().startswith(needle),
                len(item["name"]),
                item["symbol"],
            )
        )
        response.data = matches[:30]
        return response

    def get_historical_fundamentals(self, cik: str, refresh: bool = False) -> ProviderResult:
        if not cik.isdigit() or len(cik) > 10:
            raise ProviderError("SEC: CIK inválido")
        return self.request(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json", refresh
        )

    def get_submissions(self, cik: str) -> ProviderResult:
        if not cik.isdigit() or len(cik) > 10:
            raise ProviderError("SEC: CIK inválido")
        return self.request(f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json")

    def get_income_statement(self, cik: str) -> ProviderResult:
        return self.get_historical_fundamentals(cik)

    def get_balance_sheet(self, cik: str) -> ProviderResult:
        return self.get_historical_fundamentals(cik)

    def get_cash_flow_statement(self, cik: str) -> ProviderResult:
        return self.get_historical_fundamentals(cik)

    def get_ratios(self, cik: str) -> ProviderResult:
        raise ProviderError("SEC no proporciona ratios; se calculan con inputs compatibles")
