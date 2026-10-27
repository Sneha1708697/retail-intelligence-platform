"""Item-level stock logic: loads the forecast files and works out stock status per item and store."""
import json
from math import erf, sqrt
from statistics import NormalDist

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = "hierarchy_output"
STATUS_ORDER = ["Out of stock", "Order now", "Reorder soon", "Healthy", "Overstock"]


@st.cache_resource
def load_item_data():
    """Read-only item data. cache_resource avoids copying the big tables on every rerun."""
    meta = pd.read_csv(f"{DATA_DIR}/item_meta.csv")
    fc = pd.read_parquet(f"{DATA_DIR}/item_forecast.parquet")
    hist = pd.read_parquet(f"{DATA_DIR}/item_history.parquet")
    bt = pd.read_parquet(f"{DATA_DIR}/item_backtest.parquet")
    for t in (fc, hist, bt):
        t["item_id"] = t["item_id"].astype(str)
        t["store_id"] = t["store_id"].astype(str)
    key = pd.MultiIndex.from_frame(meta[["item_id", "store_id"]])
    piv = lambda col: fc.pivot(index=["item_id", "store_id"], columns="date", values=col).reindex(key)
    f = piv("forecast")
    return dict(
        meta=meta, fc=fc, hist=hist, bt=bt,
        fc_mat=f.values.astype(float), dates=pd.DatetimeIndex(f.columns),
        adj={c: piv(c).values.astype(float) for c in ("adj_price_promo", "adj_snap_events", "adj_calendar")},
        metrics=json.load(open(f"{DATA_DIR}/item_metrics.json")),
        importance=pd.read_csv(f"{DATA_DIR}/feature_importance.csv"),
        factors=pd.read_csv(f"{DATA_DIR}/factor_effects.csv"),
    )


def _norm_cdf(x):
    return np.array([0.5 * (1 + erf(v / sqrt(2))) for v in x])


def build_items(data, service_level=95.0, lead_time=3, order_cycle=7, overstock_days=14,
                stock_override=None, store=None):
    """One row per item x store with stock status, risk and a suggested order."""
    meta, F, dates = data["meta"], data["fc_mat"], data["dates"]
    keep = np.ones(len(meta), bool) if store is None else (meta.store_id == store).values
    pos = np.flatnonzero(keep)
    m, F = meta.iloc[pos].reset_index(drop=True), F[pos]

    stock = m.stock_on_hand.values.astype(float)
    source = np.array(["simulated"] * len(m), dtype=object)
    if stock_override is not None and len(stock_override):
        ov = stock_override.copy()
        ov["k"] = ov["item_id"].astype(str) + "|" + ov["store_id"].astype(str)
        lookup = dict(zip(ov["k"], ov["stock_on_hand"].astype(float)))
        for i, k in enumerate(m.item_id + "|" + m.store_id):
            if k in lookup:
                stock[i], source[i] = max(lookup[k], 0.0), "uploaded"

    L, cycle = int(lead_time), int(order_cycle)
    z = NormalDist().inv_cdf(service_level / 100)
    sigma = m.sigma_daily.values
    sd_L = np.maximum(sigma * np.sqrt(L), 1e-6)
    mean_L = F[:, :L].sum(axis=1)
    safety = z * sigma * np.sqrt(L)
    rop = mean_L + safety
    target = F[:, : L + cycle].sum(axis=1) + safety          # order-up-to level
    fc7 = F[:, :7].mean(axis=1)
    cover = np.where(fc7 > 0.05, np.minimum(stock / np.maximum(fc7, 0.05), 99.0), 99.0)

    cum = np.cumsum(F, axis=1)
    gone = cum > stock[:, None]
    runout = pd.to_datetime(np.where(gone.any(axis=1), dates.values[gone.argmax(axis=1)], np.datetime64("NaT")))
    risk = _norm_cdf(-(stock - mean_L) / sd_L)                # P(demand in lead time > stock)
    order_qty = np.where(stock <= rop, np.ceil(np.maximum(target - stock, 0)), 0)

    status = np.full(len(m), "Healthy", dtype=object)
    status[cover > overstock_days] = "Overstock"
    status[stock <= rop] = "Reorder soon"
    status[(risk >= 0.5) | (stock < mean_L)] = "Order now"
    status[stock <= 0] = "Out of stock"

    price = m.price_now.values
    out = pd.DataFrame({
        "item_id": m.item_id, "store_id": m.store_id, "cat_id": m.cat_id, "dept_id": m.dept_id,
        "status": pd.Categorical(status, categories=STATUS_ORDER, ordered=True),
        "stock_on_hand": stock, "stock_source": source,
        "avg_daily_fc": fc7, "fc_7d": F[:, :7].sum(axis=1), "fc_28d": F.sum(axis=1),
        "days_cover": cover, "runs_out_on": runout,
        "lead_demand": mean_L, "safety_stock": safety, "reorder_point": rop, "order_up_to": target,
        "suggested_order": order_qty, "stockout_risk": risk,
        "price": price, "sales_at_risk": np.maximum(mean_L - stock, 0) * price,
        "stock_value": stock * price, "excess_value": np.maximum(stock - target, 0) * price,
        "snap_days_28": m.snap_days_28.values, "event_days_28": m.event_days_28.values,
        "promo_days_28": m.promo_days_28.values, "pos": pos,
    })
    out = out.sort_values(["status", "sales_at_risk", "stockout_risk"], ascending=[True, False, False]).reset_index(drop=True)
    return out
