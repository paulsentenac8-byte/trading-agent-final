from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.alpaca_broker import AlpacaPaperBroker, load_alpaca_config_from_app_config  # noqa: E402
from src.config import load_config  # noqa: E402

CONFIG_PATH = ROOT / "config.json"
REPORTS_DIR = ROOT / "reports"

st.set_page_config(
    page_title="Trading Agent — Dashboard",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────
# Design tokens
# ──────────────────────────────────────────────────────────

INK = "#0a0e14"
PANEL = "#11161f"
PANEL_2 = "#161d2a"
BORDER = "#222a38"
TEXT = "#e8ecf3"
TEXT_DIM = "#7c8aa3"
ACCENT = "#3ddc97"       # vert signal — gains, achat, go
ACCENT_DIM = "#1f6e4f"
WARN = "#f0b84e"         # ambre — prudence, attente
DANGER = "#ef5a6f"       # corail rouge — pertes, blocage
BLUE = "#5b8def"         # bleu — info neutre, marché


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        #MainMenu, footer, header {{visibility: hidden;}}

        .stApp {{
            background: {INK};
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {PANEL};
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] * {{
            color: {TEXT};
        }}

        /* Headings */
        h1, h2, h3 {{
            font-family: 'Inter', sans-serif;
            color: {TEXT} !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }}

        /* Top ticker bar */
        .ticker-bar {{
            display: flex;
            gap: 0;
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 1.4rem;
        }}
        .ticker-item {{
            flex: 1;
            padding: 0.85rem 1.1rem;
            border-right: 1px solid {BORDER};
        }}
        .ticker-item:last-child {{ border-right: none; }}
        .ticker-label {{
            font-size: 0.72rem;
            color: {TEXT_DIM};
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.25rem;
        }}
        .ticker-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.35rem;
            font-weight: 700;
            color: {TEXT};
        }}
        .ticker-delta {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            font-weight: 500;
            margin-top: 0.15rem;
        }}
        .up {{ color: {ACCENT}; }}
        .down {{ color: {DANGER}; }}
        .neutral {{ color: {TEXT_DIM}; }}

        /* Cards */
        .panel {{
            background: {PANEL};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 1.3rem 1.4rem;
            margin-bottom: 1.2rem;
        }}
        .panel-title {{
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: {TEXT_DIM};
            margin-bottom: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* Status pills */
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.28rem 0.75rem;
            border-radius: 20px;
            font-size: 0.76rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }}
        .pill-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}
        .pill-go {{ background: rgba(61,220,151,0.12); color: {ACCENT}; }}
        .pill-go .pill-dot {{ background: {ACCENT}; }}
        .pill-warn {{ background: rgba(240,184,78,0.12); color: {WARN}; }}
        .pill-warn .pill-dot {{ background: {WARN}; }}
        .pill-stop {{ background: rgba(239,90,111,0.12); color: {DANGER}; }}
        .pill-stop .pill-dot {{ background: {DANGER}; }}
        .pill-neutral {{ background: rgba(124,138,163,0.12); color: {TEXT_DIM}; }}
        .pill-neutral .pill-dot {{ background: {TEXT_DIM}; }}

        /* Signal rows */
        .signal-row {{
            display: flex;
            align-items: center;
            gap: 0.9rem;
            padding: 0.7rem 0.9rem;
            border-radius: 8px;
            background: {PANEL_2};
            margin-bottom: 0.5rem;
            border: 1px solid {BORDER};
        }}
        .signal-ticker {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 0.95rem;
            color: {TEXT};
            min-width: 64px;
        }}
        .signal-score {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            font-weight: 600;
            min-width: 50px;
        }}
        .signal-reason {{
            flex: 1;
            font-size: 0.78rem;
            color: {TEXT_DIM};
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        /* Buttons */
        div.stButton > button {{
            background: {ACCENT} !important;
            color: {INK} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            padding: 0.6rem 1.2rem !important;
            font-size: 0.85rem !important;
        }}
        div.stButton > button:hover {{
            background: #4fe8a8 !important;
        }}
        div.stButton > button:disabled {{
            background: {BORDER} !important;
            color: {TEXT_DIM} !important;
        }}

        /* Secondary button variant via key suffix handled in markdown badges instead */

        /* Metrics override */
        [data-testid="stMetricValue"] {{
            font-family: 'JetBrains Mono', monospace;
            color: {TEXT} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {TEXT_DIM} !important;
            font-size: 0.78rem !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* Dataframe */
        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 8px;
        }}

        /* Divider line */
        .hr-line {{
            height: 1px;
            background: {BORDER};
            margin: 1.4rem 0;
            border: none;
        }}

        /* Mono small text */
        .mono-small {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: {TEXT_DIM};
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.4rem;
            border-bottom: 1px solid {BORDER};
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {TEXT_DIM};
            font-weight: 600;
            font-size: 0.85rem;
        }}
        .stTabs [aria-selected="true"] {{
            color: {ACCENT} !important;
        }}

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox > div, .stTextArea textarea {{
            background: {PANEL_2} !important;
            color: {TEXT} !important;
            border-color: {BORDER} !important;
        }}

        /* Alerts */
        div[data-testid="stAlert"] {{
            background: {PANEL_2};
            border: 1px solid {BORDER};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────
# Data loaders
# ──────────────────────────────────────────────────────────

@st.cache_data(ttl=15, show_spinner=False)
def read_json_safe(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(ttl=15, show_spinner=False)
def read_csv_safe(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_app_config():
    try:
        return load_config(str(CONFIG_PATH))
    except Exception:
        return None


def get_broker(app_config) -> AlpacaPaperBroker | None:
    if app_config is None:
        return None
    try:
        alpaca_cfg = load_alpaca_config_from_app_config(app_config.broker)
        return AlpacaPaperBroker(alpaca_cfg)
    except Exception:
        return None


@st.cache_data(ttl=10, show_spinner=False)
def fetch_account_summary(_broker_marker: str) -> dict[str, Any]:
    # _broker_marker is used only to vary the cache key when config changes
    app_config = load_app_config()
    broker = get_broker(app_config)
    if broker is None or not broker.cfg.is_configured():
        return {"ok": False, "error": "not_configured"}
    return broker.get_account_summary()


def fmt_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def fmt_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.2f}%"


# ──────────────────────────────────────────────────────────
# Charts (Plotly, thème sombre cohérent avec le dashboard)
# ──────────────────────────────────────────────────────────

def equity_curve_chart(equity_history: list[dict[str, Any]]):
    import plotly.graph_objects as go

    fig = go.Figure()

    if not equity_history:
        fig.add_annotation(
            text="Pas encore d'historique — lance l'agent pour commencer à enregistrer la courbe.",
            showarrow=False,
            font=dict(color=TEXT_DIM, size=13),
        )
    else:
        df = pd.DataFrame(equity_history)
        df["ts"] = pd.to_datetime(df["ts"])
        fig.add_trace(
            go.Scatter(
                x=df["ts"],
                y=df["equity"],
                mode="lines",
                line=dict(color=ACCENT, width=2),
                fill="tozeroy",
                fillcolor="rgba(61,220,151,0.08)",
                name="Equity",
                hovertemplate="%{y:$,.2f}<extra></extra>",
            )
        )

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(color=TEXT_DIM, family="JetBrains Mono"),
        xaxis=dict(showgrid=False, color=TEXT_DIM, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=TEXT_DIM, zeroline=False, tickprefix="$"),
        showlegend=False,
        hovermode="x unified",
    )
    return fig


def allocation_donut(positions: list[dict[str, Any]]):
    import plotly.graph_objects as go

    fig = go.Figure()
    if not positions:
        fig.add_annotation(
            text="Aucune position ouverte",
            showarrow=False,
            font=dict(color=TEXT_DIM, size=13),
        )
        fig.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor=PANEL,
            paper_bgcolor=PANEL,
        )
        return fig

    labels = [p.get("symbol", "?") for p in positions]
    values = [abs(float(p.get("market_value", 0))) for p in positions]
    palette = [ACCENT, BLUE, WARN, "#9b7cf0", "#5fd0e8", DANGER, "#e89c5f", "#8aa3d8"]

    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=palette[: len(labels)], line=dict(color=PANEL, width=2)),
            textfont=dict(color=TEXT, family="Inter", size=12),
            hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(color=TEXT_DIM),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(size=10, color=TEXT_DIM)),
    )
    return fig


def signal_bar_chart(ranked: pd.DataFrame, top_n: int = 10):
    import plotly.graph_objects as go

    fig = go.Figure()
    if ranked.empty:
        fig.add_annotation(text="Pas encore de signaux", showarrow=False, font=dict(color=TEXT_DIM, size=13))
    else:
        top = ranked.head(top_n).sort_values("score")
        colors = [ACCENT if s >= 0 else DANGER for s in top["score"]]
        fig.add_trace(
            go.Bar(
                x=top["score"],
                y=top["symbol"],
                orientation="h",
                marker=dict(color=colors),
                hovertemplate="%{y}: score %{x:.2f}<extra></extra>",
            )
        )
    fig.update_layout(
        height=max(260, 28 * top_n),
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(color=TEXT_DIM, family="JetBrains Mono", size=11),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=True, zerolinecolor=BORDER, color=TEXT_DIM),
        yaxis=dict(showgrid=False, color=TEXT),
    )
    return fig


# ──────────────────────────────────────────────────────────
# UI components
# ──────────────────────────────────────────────────────────

def render_ticker_bar(account: dict[str, Any]) -> None:
    if not account.get("ok"):
        st.markdown(
            f"""
            <div class="ticker-bar">
                <div class="ticker-item">
                    <div class="ticker-label">Statut</div>
                    <div class="ticker-value" style="color:{WARN};font-size:1.05rem;">Alpaca non connecté</div>
                    <div class="ticker-delta neutral">Configure les clés API dans la barre latérale</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    portfolio_value = account.get("portfolio_value", 0.0)
    unrealized_pl = account.get("unrealized_pl", 0.0)
    unrealized_plpc = account.get("unrealized_plpc", 0.0)
    cash = account.get("cash", 0.0)
    buying_power = account.get("buying_power", 0.0)
    positions_count = account.get("positions_count", 0)
    pl_class = "up" if unrealized_pl >= 0 else "down"
    pl_sign = "▲" if unrealized_pl >= 0 else "▼"

    st.markdown(
        f"""
        <div class="ticker-bar">
            <div class="ticker-item">
                <div class="ticker-label">Valeur du portefeuille</div>
                <div class="ticker-value">{fmt_money(portfolio_value)}</div>
                <div class="ticker-delta {pl_class}">{pl_sign} {fmt_money(unrealized_pl)} ({fmt_pct(unrealized_plpc)})</div>
            </div>
            <div class="ticker-item">
                <div class="ticker-label">Cash disponible</div>
                <div class="ticker-value">{fmt_money(cash)}</div>
                <div class="ticker-delta neutral">Pouvoir d'achat {fmt_money(buying_power)}</div>
            </div>
            <div class="ticker-item">
                <div class="ticker-label">Positions ouvertes</div>
                <div class="ticker-value">{positions_count}</div>
                <div class="ticker-delta neutral">{account.get('open_orders_count', 0)} ordre(s) en attente</div>
            </div>
            <div class="ticker-item">
                <div class="ticker-label">Mode</div>
                <div class="ticker-value" style="font-size:1.05rem;">{'Paper' if account.get('paper') else 'Live'}</div>
                <div class="ticker-delta neutral">{account.get('status', 'unknown')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label: str, level: str) -> str:
    cls = {"go": "pill-go", "warn": "pill-warn", "stop": "pill-stop"}.get(level, "pill-neutral")
    return f'<span class="pill {cls}"><span class="pill-dot"></span>{label}</span>'


def render_health_strip() -> None:
    validation = read_json_safe(str(REPORTS_DIR / "validation_summary.json"))
    killswitch = read_json_safe(str(REPORTS_DIR / "kill_switch_summary.json"))
    metarisk = read_json_safe(str(REPORTS_DIR / "meta_risk_summary.json"))
    readiness = read_json_safe(str(REPORTS_DIR / "readiness_summary.json"))

    cols = st.columns(4)
    with cols[0]:
        health = validation.get("health_score", None)
        level = "go" if (health or 0) >= 70 else "warn" if (health or 0) >= 50 else "stop"
        label = f"Santé système {health}/100" if health is not None else "Santé système — n/a"
        st.markdown(status_pill(label, level if health is not None else "neutral"), unsafe_allow_html=True)
    with cols[1]:
        blocked = killswitch.get("blocked", None)
        level = "stop" if blocked else "go" if blocked is not None else "neutral"
        label = "Kill switch activé" if blocked else "Kill switch: ok" if blocked is not None else "Kill switch — n/a"
        st.markdown(status_pill(label, level), unsafe_allow_html=True)
    with cols[2]:
        conf = metarisk.get("confidence_score", None)
        level = "go" if (conf or 0) >= 70 else "warn" if (conf or 0) >= 45 else "stop"
        label = f"Confiance risque {conf}/100" if conf is not None else "Confiance risque — n/a"
        st.markdown(status_pill(label, level if conf is not None else "neutral"), unsafe_allow_html=True)
    with cols[3]:
        score = readiness.get("readiness_score", None)
        level = "go" if (score or 0) >= 85 else "warn" if (score or 0) >= 70 else "stop"
        label = f"Readiness {score}/100" if score is not None else "Readiness — n/a"
        st.markdown(status_pill(label, level if score is not None else "neutral"), unsafe_allow_html=True)


def render_signals_panel() -> pd.DataFrame:
    ranked = read_csv_safe(str(REPORTS_DIR / "ranked_signals.csv"))
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Signaux classés</div>', unsafe_allow_html=True)
    if ranked.empty:
        st.markdown(
            f'<div class="mono-small">Aucun signal pour le moment. Lance une analyse depuis la barre latérale.</div>',
            unsafe_allow_html=True,
        )
    else:
        import plotly.graph_objects as go  # noqa: F401  (ensures plotly import error surfaces early if missing)

        st.plotly_chart(signal_bar_chart(ranked, top_n=10), use_container_width=True, config={"displayModeBar": False})
        for _, row in ranked.head(8).iterrows():
            score = float(row.get("score", 0))
            color = ACCENT if score >= 1.5 else WARN if score >= 0 else DANGER
            reasons = str(row.get("reasons", ""))[:90]
            st.markdown(
                f"""
                <div class="signal-row">
                    <span class="signal-ticker">{row.get('symbol', '?')}</span>
                    <span class="signal-score" style="color:{color}">{score:+.2f}</span>
                    <span class="signal-reason">{reasons}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)
    return ranked


def render_orders_panel(account: dict[str, Any]) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Ordres en attente</div>', unsafe_allow_html=True)
    open_orders = account.get("open_orders", []) if account.get("ok") else []
    if not open_orders:
        st.markdown('<div class="mono-small">Aucun ordre ouvert actuellement.</div>', unsafe_allow_html=True)
    else:
        rows = []
        for o in open_orders:
            rows.append(
                {
                    "Symbole": o.get("symbol", ""),
                    "Côté": o.get("side", ""),
                    "Qté": o.get("qty", ""),
                    "Type": o.get("order_class", o.get("type", "")),
                    "Statut": o.get("status", ""),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_positions_panel(account: dict[str, Any]) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Répartition des positions</div>', unsafe_allow_html=True)
    positions = account.get("positions", []) if account.get("ok") else []
    st.plotly_chart(allocation_donut(positions), use_container_width=True, config={"displayModeBar": False})
    if positions:
        rows = []
        for p in positions:
            pl = float(p.get("unrealized_pl", 0))
            rows.append(
                {
                    "Symbole": p.get("symbol", ""),
                    "Qté": p.get("qty", ""),
                    "Prix moyen": fmt_money(float(p.get("avg_entry_price", 0))),
                    "Prix actuel": fmt_money(float(p.get("current_price", 0))),
                    "P&L": fmt_money(pl),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_macro_panel() -> None:
    macro = read_json_safe(str(REPORTS_DIR / "macro_context.json")) or read_json_safe(str(REPORTS_DIR / "breadth_context.json"))
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Contexte marché</div>', unsafe_allow_html=True)
    if not macro:
        st.markdown('<div class="mono-small">Pas encore de contexte macro disponible.</div>', unsafe_allow_html=True)
    else:
        bias = macro.get("bias", macro.get("breadth_bias", 0.0))
        color = ACCENT if bias > 0.05 else DANGER if bias < -0.05 else TEXT_DIM
        st.markdown(
            f'<div style="font-family:JetBrains Mono;font-size:1.6rem;font-weight:700;color:{color}">{bias:+.2f}</div>',
            unsafe_allow_html=True,
        )
        for line in macro.get("summary", [])[:5]:
            st.markdown(f'<div class="mono-small" style="margin-bottom:0.3rem;">• {line}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar(app_config) -> dict[str, Any]:
    st.sidebar.markdown("### ◆ Trading Agent")
    st.sidebar.markdown('<div class="mono-small">Dashboard premium — paper trading Alpaca</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")

    broker = get_broker(app_config)
    configured = broker is not None and broker.cfg.is_configured()

    if configured:
        st.sidebar.success("Clés Alpaca détectées")
    else:
        st.sidebar.warning("Clés Alpaca absentes")
        st.sidebar.markdown(
            '<div class="mono-small">Ajoute <code>ALPACA_API_KEY</code> et '
            '<code>ALPACA_API_SECRET</code> dans Render → Environment, '
            'puis recharge cette page.</div>',
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Actions")

    run_analysis = st.sidebar.button("Lancer une analyse", use_container_width=True)
    refresh = st.sidebar.button("Rafraîchir les données", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Sécurité")
    paper_only = app_config.broker.paper_only if app_config else True
    st.sidebar.markdown(
        status_pill("Paper only actif" if paper_only else "Mode réel activé", "go" if paper_only else "stop"),
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="mono-small" style="margin-top:0.6rem;">'
        'Le mode réel ne doit être activé qu\'après plusieurs semaines '
        'de paper trading validées.</div>',
        unsafe_allow_html=True,
    )

    return {"run_analysis": run_analysis, "refresh": refresh}


def main() -> None:
    inject_css()

    app_config = load_app_config()
    actions = render_sidebar(app_config)

    if actions["refresh"]:
        st.cache_data.clear()

    st.markdown("## Tableau de bord trading")
    st.markdown(
        f'<div class="mono-small" style="margin-bottom:1.2rem;">'
        f'Dernière mise à jour locale: {datetime.now().strftime("%H:%M:%S")} — '
        f'données rafraîchies automatiquement toutes les 15s</div>',
        unsafe_allow_html=True,
    )

    broker = get_broker(app_config)
    marker = "configured" if (broker and broker.cfg.is_configured()) else "unconfigured"
    account = fetch_account_summary(marker)

    render_ticker_bar(account)
    render_health_strip()

    st.markdown('<hr class="hr-line">', unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Courbe d\'équité</div>', unsafe_allow_html=True)
        equity_history = []
        equity_path = REPORTS_DIR / "equity_curve.json"
        if equity_path.exists():
            try:
                equity_history = json.loads(equity_path.read_text(encoding="utf-8"))
            except Exception:
                equity_history = []
        st.plotly_chart(equity_curve_chart(equity_history), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        ranked = render_signals_panel()

    with col_right:
        render_positions_panel(account)
        render_macro_panel()

    render_orders_panel(account)

    if actions["run_analysis"]:
        st.info(
            "Pour lancer une analyse complète, exécute `python main.py` depuis le terminal Render "
            "(Shell) ou programme une tâche planifiée. Ce dashboard affiche les résultats des "
            "dernières exécutions, il ne relance pas le pipeline lui-même."
        )


if __name__ == "__main__":
    main()

