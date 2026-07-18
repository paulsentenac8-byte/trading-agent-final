from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .scalars import to_float, to_int


# ──────────────────────────────────────────────────────────
# Alpaca = courtier US avec paper trading 100% gratuit.
# Fonctionne via simples appels HTTP (pas de SDK requis),
# donc compatible avec un serveur distant comme Render —
# contrairement à IBKR qui exige TWS sur la machine locale.
# ──────────────────────────────────────────────────────────


@dataclass
class AlpacaConfig:
    api_key: str = ""
    api_secret: str = ""
    paper: bool = True
    use_bracket_orders: bool = True

    @property
    def base_url(self) -> str:
        return "https://paper-api.alpaca.markets" if self.paper else "https://api.alpaca.markets"

    @property
    def data_url(self) -> str:
        return "https://data.alpaca.markets"

    def is_configured(self) -> bool:
        return bool(self.api_key) and bool(self.api_secret)


@dataclass
class AlpacaOrderResult:
    symbol: str
    side: str
    qty: int
    order_type: str
    reference_price: float
    stop_loss: float
    take_profit: float
    rationale: str
    alpaca_order_id: str = ""
    status: str = "not_submitted"
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _headers(cfg: AlpacaConfig) -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": cfg.api_key,
        "APCA-API-SECRET-KEY": cfg.api_secret,
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, cfg: AlpacaConfig, payload: dict | None = None, timeout: float = 15.0) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(cfg), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        raise RuntimeError(f"Alpaca HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Alpaca non joignable: {exc}") from exc


class AlpacaPaperBroker:
    """
    Broker Alpaca (paper ou live selon AlpacaConfig.paper).

    Conçu pour fonctionner depuis un serveur distant (Render) car il
    n'utilise que des appels HTTP — pas de connexion locale type TWS/IBKR.
    """

    def __init__(self, config: AlpacaConfig) -> None:
        self.cfg = config

    # ── Compte ────────────────────────────────────────────

    def check_connection(self) -> tuple[bool, str]:
        if not self.cfg.is_configured():
            return False, "Clés API Alpaca non configurées."
        try:
            acct = self.get_account()
            status = acct.get("status", "unknown")
            return True, f"Connecté. Statut du compte: {status}."
        except Exception as exc:
            return False, f"Connexion Alpaca impossible: {exc}"

    def get_account(self) -> dict[str, Any]:
        return _request("GET", f"{self.cfg.base_url}/v2/account", self.cfg)

    def get_positions(self) -> list[dict[str, Any]]:
        result = _request("GET", f"{self.cfg.base_url}/v2/positions", self.cfg)
        return result if isinstance(result, list) else []

    def get_open_orders(self) -> list[dict[str, Any]]:
        result = _request("GET", f"{self.cfg.base_url}/v2/orders?status=open&limit=50", self.cfg)
        return result if isinstance(result, list) else []

    def close_all_positions(self) -> dict[str, Any]:
        """Liquide toutes les positions ouvertes (utile pour la clôture en fin de journée)."""
        return _request("DELETE", f"{self.cfg.base_url}/v2/positions", self.cfg)

    def cancel_all_orders(self) -> dict[str, Any]:
        return _request("DELETE", f"{self.cfg.base_url}/v2/orders", self.cfg)

    def get_account_summary(self) -> dict[str, Any]:
        """Résumé compact du compte pour affichage dans l'interface."""
        try:
            acct = self.get_account()
            positions = self.get_positions()
            open_orders = self.get_open_orders()
            return {
                "ok": True,
                "paper": self.cfg.paper,
                "status": acct.get("status", "unknown"),
                "portfolio_value": to_float(acct.get("portfolio_value")),
                "cash": to_float(acct.get("cash")),
                "buying_power": to_float(acct.get("buying_power")),
                "equity": to_float(acct.get("equity")),
                "unrealized_pl": to_float(acct.get("unrealized_pl")),
                "unrealized_plpc": to_float(acct.get("unrealized_plpc")),
                "daytrade_count": to_int(acct.get("daytrade_count")),
                "positions_count": len(positions),
                "open_orders_count": len(open_orders),
                "positions": positions,
                "open_orders": open_orders,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Ordres ────────────────────────────────────────────

    def _submit_bracket_order(self, symbol: str, qty: int, limit_price: float, stop_loss: float, take_profit: float) -> dict[str, Any]:
        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": "buy",
            "type": "limit",
            "time_in_force": "day",
            "limit_price": f"{limit_price:.2f}",
            "order_class": "bracket",
            "take_profit": {"limit_price": f"{take_profit:.2f}"},
            "stop_loss": {"stop_price": f"{stop_loss:.2f}"},
        }
        return _request("POST", f"{self.cfg.base_url}/v2/orders", self.cfg, payload)

    def _submit_market_order(self, symbol: str, side: str, qty: int) -> dict[str, Any]:
        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        return _request("POST", f"{self.cfg.base_url}/v2/orders", self.cfg, payload)

    def submit_trade_plan(
        self,
        trade_plan: pd.DataFrame,
        dry_run: bool = True,
        output_path: str = "reports/alpaca_orders.json",
    ) -> tuple[list[AlpacaOrderResult], Path]:
        """
        Envoie le trade_plan (issu de build_trade_plan + pretrade) à Alpaca.

        dry_run=True  : ne contacte pas Alpaca, simule juste le résultat (sûr par défaut).
        dry_run=False : envoie réellement les ordres au compte configuré (paper ou live).
        """
        results: list[AlpacaOrderResult] = []

        if trade_plan.empty:
            return results, _write_results(results, output_path)

        for _, row in trade_plan.iterrows():
            symbol = str(row.get("symbol", ""))
            qty = to_int(row.get("qty"))
            close = to_float(row.get("close"))
            stop_loss = to_float(row.get("stop_loss", close * 0.95))
            take_profit = to_float(row.get("take_profit", close * 1.10))
            rationale = str(row.get("reasons", ""))[:300]

            if qty <= 0 or close <= 0 or not symbol:
                continue

            order = AlpacaOrderResult(
                symbol=symbol,
                side="buy",
                qty=qty,
                order_type="bracket" if self.cfg.use_bracket_orders else "market",
                reference_price=close,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=rationale,
            )

            if dry_run:
                order.status = "dry_run"
            else:
                try:
                    if self.cfg.use_bracket_orders:
                        resp = self._submit_bracket_order(symbol, qty, close, stop_loss, take_profit)
                    else:
                        resp = self._submit_market_order(symbol, "buy", qty)
                    order.alpaca_order_id = str(resp.get("id", ""))
                    order.status = str(resp.get("status", "submitted"))
                except Exception as exc:
                    order.status = "error"
                    order.error = str(exc)
                time.sleep(0.3)  # respecte le rate limit Alpaca

            results.append(order)

        return results, _write_results(results, output_path)


def _write_results(results: list[AlpacaOrderResult], output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_alpaca_config_from_app_config(broker_config: Any) -> AlpacaConfig:
    """
    Construit AlpacaConfig à partir de BrokerConfig (src/config.py) + variables
    d'environnement. Les clés API ne sont jamais stockées en dur dans config.json :
    elles viennent des variables d'environnement Render (ALPACA_API_KEY / ALPACA_API_SECRET).
    """
    import os

    api_key = os.environ.get("ALPACA_API_KEY", "")
    api_secret = os.environ.get("ALPACA_API_SECRET", "")
    paper = getattr(broker_config, "paper_only", True)
    use_bracket = getattr(broker_config, "alpaca_use_bracket_orders", True)

    return AlpacaConfig(
        api_key=api_key,
        api_secret=api_secret,
        paper=paper,
        use_bracket_orders=use_bracket,
    )
