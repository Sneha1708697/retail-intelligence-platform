from common import *

c = get_context()
hero("Store policy", "Store-level safety stock, reorder points and order sizes, plus the 28-day stockout backtest")
inv = c["inv"]
st.caption(f"Policy: {c['service_level']:.1f}% service level · {c['lead_time']}-day lead time. Change these in the sidebar.")

display = inv[["avg_daily_demand", "forecast_error_std", "safety_stock", "reorder_point", "eoq_order_qty"]].round(1)
display.columns = ["Avg daily demand", "Forecast error (σ)", "Safety stock", "Reorder point", "Order qty (EOQ)"]
display.index.name = "Store"
try:
    st.dataframe(display, width="stretch")
except Exception:
    st.dataframe(display, use_container_width=True)
st.download_button("Download inventory plan (CSV)", display.to_csv().encode("utf-8"), "inventory_plan.csv", "text/csv")

a, b = st.columns(2)
with a:
    st.markdown("### Safety stock")
    show(style_fig(go.Figure(go.Bar(x=inv.index, y=inv["safety_stock"], marker_color=BLUE)), 320))
with b:
    st.markdown("### Recommended order quantity")
    show(style_fig(go.Figure(go.Bar(x=inv.index, y=inv["eoq_order_qty"], marker_color=YELLOW)), 320))

st.markdown("### Stockout backtest")
st.caption("28-day simulation run at a 95% service level and 3-day lead time.")
sim = c["sim"]
fig = go.Figure(go.Bar(x=sim["store"], y=sim["stockout_rate"], marker_color=[RED if r > TARGET_STOCKOUT_RATE else BLUE for r in sim["stockout_rate"]]))
fig.add_hline(y=TARGET_STOCKOUT_RATE, line_dash="dash", line_color=MUTED, annotation_text="5% target")
fig = style_fig(fig, 340)
fig.update_yaxes(tickformat=".0%")
show(fig)
