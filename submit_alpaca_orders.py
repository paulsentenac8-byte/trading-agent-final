from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.alpaca_broker import AlpacaPaperBroker, load_alpaca_config_from_app_config
from src.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Soumission d'ordres approuvés vers Alpaca (paper ou live)")
    parser.add_argument("--config", default="config.json", help="Chemin vers le fichier config")
    parser.add_argument("--orders", default="reports/orders_to_review.csv", help="CSV des ordres revus")
    parser.add_argument("--dry-run", action="store_true", help="Simule seulement, n'envoie rien à Alpaca")
    parser.add_argument("--submit", action="store_true", help="Envoie réellement les ordres au compte configuré")
    return parser.parse_args()


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "oui"}


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    orders_path = Path(args.orders)
    if not orders_path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {orders_path}")

    review_df = pd.read_csv(orders_path)
    if "approved" in review_df.columns:
        review_df = review_df[review_df["approved"].apply(_truthy)].copy()

    if args.submit and not config.broker.paper_only:
        raise ValueError(
            "Pour la sécurité, garde broker.paper_only=true tant que le système n'a pas "
            "été validé pendant plusieurs semaines en paper trading."
        )

    dry_run = True
    if args.submit:
        dry_run = False
    elif args.dry_run:
        dry_run = True

    alpaca_cfg = load_alpaca_config_from_app_config(config.broker)
    if not dry_run and not alpaca_cfg.is_configured():
        raise ValueError(
            "Clés API Alpaca manquantes. Configure ALPACA_API_KEY et ALPACA_API_SECRET "
            "dans les variables d'environnement (Render > Environment)."
        )

    broker = AlpacaPaperBroker(alpaca_cfg)

    results, output_path = broker.submit_trade_plan(
        trade_plan=review_df,
        dry_run=dry_run,
        output_path=str(orders_path.parent / "alpaca_orders_log.json"),
    )

    mode = "DRY RUN (rien envoyé)" if dry_run else f"SUBMIT ({'PAPER' if alpaca_cfg.paper else 'LIVE'})"
    print(f"Mode: {mode}")
    print(f"Ordres traités: {len(results)}")
    print(f"Journal: {output_path}")
    for r in results:
        status_line = f"  {r.symbol}: {r.status}"
        if r.error:
            status_line += f" — erreur: {r.error}"
        print(status_line)


if __name__ == "__main__":
    main()
