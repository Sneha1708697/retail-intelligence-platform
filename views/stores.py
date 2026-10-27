from common import *

c = get_context()
hero("Stores", "Drill into one store's demand pattern and inventory plan")
s = st.selectbox("Store", c["store"].columns.tolist())
row, sim_idx = c["inv"].loc[s], c["sim"].set_index("store")
rate = float(sim_idx.loc[s, "stockout_rate"])
status = badge("Stockout risk", "red") if s in c["stockout"] else badge("Overstock", "yellow") if s in c["overstock"] else badge("Healthy", "green")

k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Avg daily demand", f"{row['avg_daily_demand']:,.0f}", "units", BLUE), unsafe_allow_html=True)
k2.markdown(kpi("Safety stock", f"{row['safety_stock']:,.0f}", "units", YELLOW), unsafe_allow_html=True)
k3.markdown(kpi("Reorder point", f"{row['reorder_point']:,.0f}", f"Order {row['eoq_order_qty']:,.0f} units", BLUE), unsafe_allow_html=True)
k4.markdown(kpi("Stockout rate", f"{rate:.1%}", status, YELLOW), unsafe_allow_html=True)

st.markdown("### Stock status in this store")
sub = c["items"][c["items"].store_id == s]
cc = st.columns(len(STATUS_ORDER))
for col, name in zip(cc, STATUS_ORDER):
    col.markdown(kpi(STATUS_STYLE[name][0], f"{int((sub.status == name).sum())}", "products", STATUS_STYLE[name][2]), unsafe_allow_html=True)
need = sub[sub.status.isin(["Out of stock", "Order now"])].head(5)
if len(need):
    st.markdown(items_table_html(need, show_store=False), unsafe_allow_html=True)

st.markdown("### Demand history")
y = c["store"][s]
fig = go.Figure()
fig.add_trace(go.Scatter(x=y.index, y=y, name="Daily", line=dict(color=SKY, width=1)))
fig.add_trace(go.Scatter(x=y.index, y=y.rolling(28).mean(), name="28-day average", line=dict(color=BLUE, width=2.5)))
show(style_fig(fig, 340))

a, b = st.columns(2)
with a:
    st.markdown("### Typical week")
    wk = y.groupby(y.index.dayofweek).mean()
    show(style_fig(go.Figure(go.Bar(x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], y=wk.values, marker_color=BLUE)), 300))
with b:
    st.markdown("### Compared with other stores")
    avg = c["store"].mean()
    show(style_fig(go.Figure(go.Bar(x=avg.index, y=avg.values, marker_color=[YELLOW if i == s else SKY for i in avg.index])), 300))
