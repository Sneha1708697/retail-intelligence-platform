from common import *

c = get_context()
data = c["item_data"]
m = data["metrics"]
hero("Forecast insights", "How accurate the forecasts are, and what drives them")

# ---------- accuracy ----------
st.markdown("### How accurate are the forecasts?")
lv = m["levels"]
order = ["Item x store", "Store", "Department", "Category", "Total (these items)"]
cols = st.columns(4)
for col, name in zip(cols, ["Item x store", "Store", "Category", "Total (these items)"]):
    col.markdown(kpi(f"Error · {name}", f"{lv[name]['model'] * 100:.1f}%", f"simple baseline {lv[name]['naive'] * 100:.1f}%", BLUE if name != "Item x store" else YELLOW), unsafe_allow_html=True)

left, right = st.columns([3, 2])
with left:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=order, y=[lv[k]["naive"] * 100 for k in order], name="Simple baseline", marker_color="#9AA5B1"))
    fig.add_trace(go.Bar(x=order, y=[lv[k]["model"] * 100 for k in order], name="This model", marker_color=BLUE))
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_yaxes(title="Error (WAPE, %) - lower is better")
    show(style_fig(fig, 340))
with right:
    st.markdown(
        f"- Tested on the **last 28 days** of data, which the model had not seen.\n"
        f"- The model covers **{m['n_items']} products** (top {m['top_per_dept']} in each department) across all stores, "
        f"about **{m['coverage'] * 100:.0f}%** of company sales.\n"
        "- The baseline repeats the sales from the same day four weeks earlier.\n"
        "- A single product in a single store sells only a few units a day, which is partly luck, so daily error is high. "
        "Adding products up cancels the luck: error falls to a few percent for a whole store or category.\n"
        f"- Overall bias: {m['bias_pct']:+.1f}% (positive means the forecast ran high)."
    )

# ---------- drivers ----------
st.markdown("### What drives the forecast")
d1, d2 = st.columns(2)
names = {"recent_demand": "Recent sales level", "profile": "Product and store profile", "calendar": "Day of week and calendar",
         "price_promo": "Price and promotions", "snap_events": "SNAP days and events"}
grp = data["importance"].groupby("group").gain_pct.sum().sort_values()
with d1:
    st.markdown("**How much weight the model gives each group of factors**")
    fig = go.Figure(go.Bar(y=[names[g] for g in grp.index], x=grp.values, orientation="h", marker_color=BLUE,
                           text=[f"{v:.1f}%" for v in grp.values], textposition="outside"))
    fig.update_xaxes(title="Share of model weight (%)")
    show(style_fig(fig, 320))
with d2:
    st.markdown("**How much sales move on those days (all products)**")
    fx = data["factors"].copy()
    fx["label"] = np.where(fx.factor == "Day of week", fx.level, fx.factor)
    fx = fx.sort_values("lift_pct")
    fig = go.Figure(go.Bar(y=fx.label, x=fx.lift_pct, orientation="h", marker_color=[BLUE if v >= 0 else "#9AA5B1" for v in fx.lift_pct],
                           text=[f"{v:+.1f}%" for v in fx.lift_pct], textposition="outside"))
    fig.update_xaxes(title="Sales vs a normal day (%)")
    show(style_fig(fig, 320))
st.markdown(
    '<div class="note">Weekends and SNAP benefit days lift sales; midweek days and holidays run lower. '
    'The model uses all of these, price and promotions too, but recent sales explain most of what happens next. '
    'In the sample data, price cuts changed sales very little for these products.</div>', unsafe_allow_html=True)

# ---------- backtest explorer ----------
st.markdown("### Check one product against what actually sold")
bt = data["bt"]
meta = data["meta"]
vol = meta.groupby("item_id").mean_fc_28.sum().sort_values(ascending=False)
b1, b2 = st.columns([2, 1])
item = b1.selectbox("Product", vol.index.tolist(), key="bt_item")
store = b2.selectbox("Store", sorted(meta.store_id.unique()), key="bt_store")
b = bt[(bt.item_id == item) & (bt.store_id == store)].sort_values("date")
fig = go.Figure()
fig.add_trace(go.Scatter(x=b.date, y=b.actual, name="Actual", line=dict(color=NAVY, width=2.2)))
fig.add_trace(go.Scatter(x=b.date, y=b.pred, name="Model forecast", line=dict(color=BLUE, width=2.5)))
fig.add_trace(go.Scatter(x=b.date, y=b.naive, name="Simple baseline", line=dict(color="#9AA5B1", width=1.5, dash="dot")))
show(style_fig(fig, 320))
if len(b):
    st.caption(f"Over these 28 days: actual {b.actual.sum():,.0f} units, model {b.pred.sum():,.0f}, baseline {b.naive.sum():,.0f}.")

# ---------- hierarchical reconciliation (store level) ----------
st.markdown("### Store-level reconciliation")
st.caption("Forecasting the company total directly versus adding up store forecasts, and blending them with MinT reconciliation.")
f = c["forecast"]
fig = go.Figure()
fig.add_trace(go.Scatter(x=f["date"], y=f["actual"], name="Actual", line=dict(color=NAVY, width=2.5)))
fig.add_trace(go.Scatter(x=f["date"], y=f["direct_forecast"], name="Direct", line=dict(color=YELLOW, dash="dot")))
fig.add_trace(go.Scatter(x=f["date"], y=f["bottom_up_forecast"], name="Bottom-Up", line=dict(color=SKY, dash="dash")))
fig.add_trace(go.Scatter(x=f["date"], y=f["mint_reconciled_forecast"], name="MinT Reconciled", line=dict(color=BLUE, width=2.5)))
show(style_fig(fig, 340))
mm = c["mae"]
st.markdown(
    f"- Average error per day: Direct **{mm['Direct']:,.0f}**, Bottom-Up **{mm['Bottom-Up']:,.0f}**, MinT Reconciled **{mm['MinT Reconciled']:,.0f}** units.\n"
    f"- {c['best_name']} was best, {c['improvement']:.1f}% better than forecasting the total directly."
)
