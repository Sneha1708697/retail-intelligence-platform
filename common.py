"""Shared styling, data loading and calculations used by every page."""
from statistics import NormalDist

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from items import STATUS_ORDER  # noqa: F401  (re-exported for the pages)

DATA_DIR = "hierarchy_output"
TARGET_STOCKOUT_RATE = 0.05

# ---------- Palette (retail blue + yellow) ----------
BLUE = "#0071CE"
BLUE_DARK = "#004F9A"
NAVY = "#041E42"
YELLOW = "#FFC220"
SKY = "#6CB4EE"
BG = "#F2F4F7"
LINE = "#E3E7ED"
TEXT = "#1F2937"
MUTED = "#6B7280"
GREEN = "#2A8703"
RED = "#D92D20"

# one colour per category everywhere (colour follows the entity, never its rank)
CAT_COLORS = {"FOODS": BLUE, "HOBBIES": YELLOW, "HOUSEHOLD": SKY}
STATUS_STYLE = {  # label, badge class, chart colour
    "Out of stock": ("⛔ Out of stock", "red", RED),
    "Order now": ("● Order now", "red", "#F04438"),
    "Reorder soon": ("● Reorder soon", "amber", "#F79009"),
    "Healthy": ("✓ Healthy", "green", GREEN),
    "Overstock": ("▲ Overstock", "blue", BLUE),
}

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stApp { font-family: 'Nunito Sans', sans-serif; color: __TEXT__; }
.stApp { background: __BG__; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }
div[data-testid="stToolbar"] { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: __NAVY__; font-weight: 800; letter-spacing: -0.01em; }
h3 { font-size: 1.15rem !important; }

section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid __LINE__; }

.hero {
    background: linear-gradient(90deg, __BLUE_DARK__, __BLUE__);
    color: #FFFFFF; padding: 1.3rem 1.6rem; border-radius: 14px;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 5px solid __YELLOW__; margin-bottom: 1rem;
}
.hero-title { font-size: 1.75rem; font-weight: 800; line-height: 1.2; }
.hero-sub { opacity: .92; font-size: .95rem; margin-top: .15rem; }
.hero-pill {
    background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.4);
    padding: .35rem .85rem; border-radius: 999px; font-size: .8rem; font-weight: 700; white-space: nowrap;
}

.kpi {
    background: #FFFFFF; border: 1px solid __LINE__; border-radius: 12px;
    padding: 1rem 1.1rem; box-shadow: 0 1px 3px rgba(16,24,40,.08);
}
.kpi-label { color: __MUTED__; font-size: .76rem; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; }
.kpi-value { color: __NAVY__; font-size: 1.9rem; font-weight: 800; line-height: 1.25; }
.kpi-sub { font-size: .83rem; font-weight: 700; }

.callout {
    background: #FFF8E1; border: 1px solid #FFE08A; border-left: 5px solid __YELLOW__;
    border-radius: 10px; padding: .8rem 1rem; margin: .9rem 0 1.1rem; color: __TEXT__;
}

.badge { display: inline-block; padding: .15rem .65rem; border-radius: 999px; font-size: .75rem; font-weight: 800; }
.badge-green { background: #E6F4EA; color: __GREEN__; }
.badge-red { background: #FDE8E7; color: __RED__; }
.badge-yellow { background: #FFF3CD; color: #8A6100; }

table.health { width: 100%; border-collapse: collapse; background: #FFFFFF; border: 1px solid __LINE__; border-radius: 12px; overflow: hidden; }
table.health th { text-align: left; background: #F8FAFC; color: __MUTED__; font-size: .74rem; text-transform: uppercase; letter-spacing: .05em; padding: .65rem .85rem; border-bottom: 1px solid __LINE__; }
table.health td { padding: .65rem .85rem; border-bottom: 1px solid #F1F3F6; font-size: .9rem; }

.alert-card { background: #FFFFFF; border: 1px solid __LINE__; border-left-width: 5px; border-radius: 10px; padding: .85rem 1.1rem; margin-bottom: .65rem; }
.alert-title { font-weight: 800; color: __NAVY__; margin-bottom: .15rem; }
.alert-body { font-size: .9rem; color: __TEXT__; }

div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
    background: #FFFFFF; border: 1px solid __LINE__; border-radius: 12px; padding: .5rem;
    box-shadow: 0 1px 3px rgba(16,24,40,.06);
}

button[data-baseweb="tab"] { font-weight: 800; color: __MUTED__; }
button[data-baseweb="tab"][aria-selected="true"] { color: __BLUE__ !important; }
div[data-baseweb="tab-highlight"] { background-color: __BLUE__ !important; height: 3px; }

.stDownloadButton button { background: __BLUE__; color: #FFFFFF; border: none; border-radius: 999px; font-weight: 800; padding: .45rem 1.3rem; }
.stDownloadButton button:hover { background: __BLUE_DARK__; color: #FFFFFF; }

.badge-blue { background: #E1EFFB; color: __BLUE_DARK__; }
.badge-gray { background: #EEF0F3; color: __MUTED__; }
.badge-amber { background: #FEF0C7; color: #93370D; }
.note { background: #FFFFFF; border: 1px solid __LINE__; border-radius: 10px; padding: .7rem 1rem; color: __MUTED__; font-size: .88rem; margin: .4rem 0 1rem; }
.usercard { background: #F2F4F7; border: 1px solid __LINE__; border-radius: 10px; padding: .6rem .8rem; margin-bottom: .6rem; }
.usercard b { color: __NAVY__; }
.login-hero { text-align: center; padding: 2.2rem 1rem 1.4rem; background: linear-gradient(90deg, __BLUE_DARK__, __BLUE__); border-bottom: 5px solid __YELLOW__; border-radius: 14px; margin-bottom: 1.6rem; color: #FFFFFF; }
.login-logo { font-size: 2.4rem; }
.login-title { font-size: 2rem; font-weight: 800; }
.login-sub { opacity: .92; margin-top: .2rem; }
.status-dot { display: inline-block; width: .6rem; height: .6rem; border-radius: 50%; margin-right: .35rem; }
</style>
"""
for token, value in {
    "__TEXT__": TEXT, "__BG__": BG, "__NAVY__": NAVY, "__LINE__": LINE, "__MUTED__": MUTED,
    "__BLUE__": BLUE, "__BLUE_DARK__": BLUE_DARK, "__YELLOW__": YELLOW, "__GREEN__": GREEN, "__RED__": RED,
}.items():
    CSS = CSS.replace(token, value)
# blank lines inside an HTML block make Streamlit print the CSS as text, so strip them
CSS = "\n".join(line for line in CSS.splitlines() if line.strip())


# ---------- Helpers ----------
def kpi(label, value, sub="", accent=BLUE, sub_color=MUTED):
    return (
        f'<div class="kpi" style="border-top:4px solid {accent}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub" style="color:{sub_color}">{sub}</div></div>'
    )


def style_fig(fig, height=340):
    fig.update_layout(
        height=height,
        margin=dict(t=30, b=20, l=10, r=10),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Nunito Sans, sans-serif", color=TEXT, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#EEF1F5", zeroline=False),
        yaxis=dict(gridcolor="#EEF1F5", zeroline=False),
    )
    return fig


def show(fig):
    """Render a Plotly chart full-width on both old and new Streamlit versions."""
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def badge(text, kind):
    return f'<span class="badge badge-{kind}">{text}</span>'



def setup():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle, pill=None):
    pill = pill or f"● {scope_label()}"
    st.markdown(
        f'<div class="hero"><div><div class="hero-title">{title}</div>'
        f'<div class="hero-sub">{subtitle}</div></div><div class="hero-pill">{pill}</div></div>',
        unsafe_allow_html=True,
    )


@st.cache_data
def load_data():
    idx = dict(index_col=0, parse_dates=True)
    r = lambda name, **kw: pd.read_csv(f"{DATA_DIR}/{name}.csv", **kw)
    return dict(
        total=r("total_level", **idx), state=r("state_level", **idx), store=r("store_level", **idx),
        category=r("category_level", **idx), dept=r("dept_level", **idx),
        forecast=r("forecast_comparison", parse_dates=["date"]),
        inventory=r("inventory_table", index_col=0), sim=r("simulation_results"),
    )


def _chain_context():
    """Loads the data and applies the what-if settings chosen in the sidebar."""
    d = dict(load_data())
    ss = st.session_state
    sl, lt = ss.get("service_level", 95.0), ss.get("lead_time", 3)
    oc, hc = ss.get("ordering_cost", 50.0), ss.get("holding_cost", 2.0)

    f = d["forecast"]
    mae = {
        "Direct": (f["actual"] - f["direct_forecast"]).abs().mean(),
        "Bottom-Up": (f["actual"] - f["bottom_up_forecast"]).abs().mean(),
        "MinT Reconciled": (f["actual"] - f["mint_reconciled_forecast"]).abs().mean(),
    }
    best_name, best_mae = min(mae.items(), key=lambda kv: kv[1])

    inv = d.pop("inventory").copy()
    z = NormalDist().inv_cdf(sl / 100)
    inv["safety_stock"] = z * inv["forecast_error_std"] * np.sqrt(lt)
    inv["reorder_point"] = inv["avg_daily_demand"] * lt + inv["safety_stock"]
    inv["eoq_order_qty"] = np.sqrt(2 * inv["avg_daily_demand"] * 365 * oc / hc)

    ratio = inv["reorder_point"] / inv["avg_daily_demand"]
    overstock = ratio[ratio > ratio.mean() + ratio.std()].index.tolist()
    sim = d["sim"]
    stockout_df = sim[sim["stockout_rate"] > TARGET_STOCKOUT_RATE]

    d.update(
        inv=inv, mae=mae, best_name=best_name, best_mae=best_mae,
        improvement=(mae["Direct"] - best_mae) / mae["Direct"] * 100,
        ratio=ratio, overstock=overstock, stockout_df=stockout_df,
        stockout=stockout_df["store"].tolist(), n_alerts=len(overstock) + len(stockout_df),
        avg_stockout=sim["stockout_rate"].mean(), service_level=sl, lead_time=lt,
    )
    return d


def health_table(c):
    sim_idx = c["sim"].set_index("store")
    inv, rows = c["inv"], ""
    for s in inv.index:
        rate = float(sim_idx.loc[s, "stockout_rate"]) if s in sim_idx.index else 0.0
        if s in c["stockout"]:
            status = badge("Stockout risk", "red")
        elif s in c["overstock"]:
            status = badge("Overstock", "yellow")
        else:
            status = badge("Healthy", "green")
        rows += (
            f"<tr><td><b>{s}</b></td><td>{inv.loc[s, 'avg_daily_demand']:,.0f}</td>"
            f"<td>{inv.loc[s, 'safety_stock']:,.0f}</td><td>{inv.loc[s, 'reorder_point']:,.0f}</td>"
            f"<td>{rate:.1%}</td><td>{status}</td></tr>"
        )
    return (
        '<table class="health"><thead><tr><th>Store</th><th>Avg daily demand</th><th>Safety stock</th>'
        '<th>Reorder point</th><th>Stockout rate</th><th>Status</th></tr></thead><tbody>'
        + rows + "</tbody></table>"
    )


def get_user():
    return st.session_state.get("user") or {"username": "", "name": "", "role": "owner", "store": None}


def scope_store():
    """Store a manager is limited to, or None for the owner."""
    u = get_user()
    return u["store"] if u["role"] == "manager" else None


def scope_label():
    s = scope_store()
    return f"Store {s}" if s else "All 10 stores"


def status_badge(status):
    label, cls, _ = STATUS_STYLE[str(status)]
    return badge(label, cls)


def get_context():
    """Chain-level numbers (for the owner pages) plus the item-level stock table for the signed-in user."""
    import items as it
    d = _chain_context()
    data = it.load_item_data()
    ss = st.session_state
    d["item_data"] = data
    d["items"] = it.build_items(
        data, service_level=ss.get("service_level", 95.0), lead_time=ss.get("lead_time", 3),
        order_cycle=ss.get("order_cycle", 7), overstock_days=ss.get("overstock_days", 14),
        stock_override=ss.get("stock_override"), store=scope_store(),
    )
    return d


def items_table_html(df, show_store=True):
    """Compact HTML table used on Home and in the assistant page."""
    rows = ""
    for r in df.itertuples():
        runs = r.runs_out_on.strftime("%d %b") if pd.notna(r.runs_out_on) else "after 28 days"
        cover = "99+" if r.days_cover >= 99 else f"{r.days_cover:,.1f}"
        rows += (
            f"<tr><td><b>{r.item_id}</b></td>" + (f"<td>{r.store_id}</td>" if show_store else "")
            + f"<td>{r.stock_on_hand:,.0f}</td><td>{cover}</td><td>{runs}</td>"
            f"<td><b>{r.suggested_order:,.0f}</b></td><td>${r.sales_at_risk:,.0f}</td><td>{status_badge(r.status)}</td></tr>"
        )
    head = ("<tr><th>Product</th>" + ("<th>Store</th>" if show_store else "")
            + "<th>On hand</th><th>Days of cover</th><th>Runs out</th><th>Suggested order</th>"
              "<th>Sales at risk</th><th>Status</th></tr>")
    return f'<table class="health"><thead>{head}</thead><tbody>{rows}</tbody></table>'
