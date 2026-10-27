from common import *

c = get_context()
items, data = c["items"], c["item_data"]
hero("Product explorer", "Pick a category, department and product to see its sales, forecast and stock outlook")

# ---------- pickers ----------
p1, p2, p3, p4 = st.columns([1, 1, 2, 1])
cat = p1.selectbox("Category", sorted(items.cat_id.unique()))
dept = p2.selectbox("Department", sorted(items[items.cat_id == cat].dept_id.unique()))
vol = items[items.dept_id == dept].groupby("item_id").fc_28d.sum().sort_values(ascending=False)
item = p3.selectbox("Product", vol.index.tolist(), format_func=lambda i: f"{i}  ·  {vol[i]:,.0f} units forecast (28 days)")
stores_avail = sorted(items.store_id.unique())
store = p4.selectbox("Store", (["All stores"] if len(stores_avail) > 1 else []) + stores_avail)

sel = items[(items.item_id == item) & ((items.store_id == store) if store != "All stores" else True)]
pos = sel.pos.values
dates = data["dates"]
F = data["fc_mat"][pos].sum(axis=0)                                    # daily forecast (summed over chosen stores)
sig = np.sqrt((data["meta"].sigma_daily.values[pos] ** 2).sum())       # combined daily uncertainty
stock = sel.stock_on_hand.sum()
rop = sel.reorder_point.sum()

# ---------- headline numbers ----------
fc7 = F[:7].mean()
cover = min(stock / max(fc7, 0.05), 99) if fc7 > 0.05 else 99
cum = np.cumsum(F)
gone = np.flatnonzero(cum > stock)
runs = f"{dates[gone[0]]:%d %b}" if len(gone) else "after 28 days"
if len(sel) == 1:
    status_html = status_badge(sel.status.iloc[0])
else:
    n_urgent = int(sel.status.isin(["Out of stock", "Order now"]).sum())
    status_html = badge(f"{n_urgent} of {len(sel)} stores need ordering", "red" if n_urgent else "green")

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(kpi("On hand", f"{stock:,.0f}", "units", BLUE), unsafe_allow_html=True)
k2.markdown(kpi("Days of cover", "99+" if cover >= 99 else f"{cover:,.1f}", f"at {fc7:,.1f} per day", YELLOW), unsafe_allow_html=True)
k3.markdown(kpi("Runs out", runs, "if nothing arrives", RED if len(gone) and gone[0] < 14 else GREEN), unsafe_allow_html=True)
k4.markdown(kpi("Suggested order", f"{sel.suggested_order.sum():,.0f}", "units now", BLUE), unsafe_allow_html=True)
k5.markdown(kpi("Status", "", status_html, BLUE), unsafe_allow_html=True)

# ---------- sales history and forecast ----------
st.markdown("### Sales history and forecast")
h = data["hist"]
h = h[(h.item_id == item) & ((h.store_id == store) if store != "All stores" else True)]
h = h.groupby("date").sales.sum().iloc[-90:]
lo, hi = np.clip(F - 1.28 * sig, 0, None), F + 1.28 * sig
fig = go.Figure()
fig.add_trace(go.Scatter(x=h.index, y=h.values, name="Actual sales", line=dict(color=NAVY, width=1.6)))
fig.add_trace(go.Scatter(x=dates, y=hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=dates, y=lo, fill="tonexty", fillcolor="rgba(0,113,206,0.15)", line=dict(width=0), name="Likely range (80%)", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=dates, y=F, name="Forecast", line=dict(color=BLUE, width=2.5)))
fig.add_vrect(x0=dates[0], x1=dates[-1], fillcolor="#6CB4EE", opacity=0.06, line_width=0)
show(style_fig(fig, 340))

# ---------- stock outlook ----------
a, b = st.columns(2)
with a:
    st.markdown("### Stock outlook (if nothing is ordered)")
    proj = stock - cum
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=np.clip(proj, 0, None), name="Projected stock", line=dict(color=BLUE, width=2.5), fill="tozeroy", fillcolor="rgba(0,113,206,0.10)"))
    fig.add_trace(go.Scatter(x=dates, y=[rop] * len(dates), name="Reorder point", line=dict(color="#B54708", dash="dash", width=2)))
    show(style_fig(fig, 320))
    short = max(cum[-1] - stock, 0)
    st.caption(f"Over 28 days the forecast needs {cum[-1]:,.0f} units against {stock:,.0f} on hand"
               + (f", a shortfall of about {short:,.0f} units." if short > 0 else ", so stock is enough."))
with b:
    st.markdown("### Typical week for this product")
    hh = data["hist"]
    hh = hh[(hh.item_id == item) & ((hh.store_id == store) if store != "All stores" else True)].groupby("date").sales.sum()
    wk = hh.groupby(hh.index.dayofweek).mean().reindex(range(7)).fillna(0)
    avg = wk.mean() if wk.mean() > 0 else 1
    fig = go.Figure(go.Bar(x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], y=((wk / avg - 1) * 100).values, marker_color=BLUE))
    fig.update_yaxes(title="% vs average day")
    show(style_fig(fig, 320))
    st.caption("Based on the last 180 days of actual sales.")

# ---------- what is behind the forecast ----------
st.markdown("### What is behind this forecast")
l, r = st.columns([3, 2])
with l:
    adj = {k: data["adj"][k][pos].mean(axis=0) for k in ("adj_calendar", "adj_snap_events", "adj_price_promo")}
    fig = go.Figure()
    for key, name, color in [("adj_calendar", "Day of week and calendar", BLUE), ("adj_snap_events", "SNAP days and events", YELLOW), ("adj_price_promo", "Price and promotions", SKY)]:
        fig.add_trace(go.Scatter(x=dates, y=adj[key], name=name, line=dict(color=color, width=2)))
    fig.update_yaxes(title="% effect on the forecast")
    show(style_fig(fig, 320))
    st.caption("How much each factor moves the forecast on each day compared with a typical day. Approximate.")
with r:
    fi = data["importance"].groupby("group").gain_pct.sum()
    base_share = fi.get("recent_demand", 0) + fi.get("profile", 0)
    st.markdown(
        f"- **Most of the forecast** (about {base_share:.0f}% of the model's weight) comes from recent sales and this product's usual level.\n"
        f"- **Next 28 days:** {int(sel.snap_days_28.mean())} SNAP benefit days, {int(sel.event_days_28.mean())} holiday or event days, "
        f"{int(sel.promo_days_28.sum())} day(s) priced at least 5% below normal.\n"
        f"- **Uncertainty:** the shaded band is the range sales should fall in about 8 days out of 10."
    )
    st.markdown('<div class="note">Price promotions moved sales very little for these products in the sample data, so the model gives them a small weight.</div>', unsafe_allow_html=True)
