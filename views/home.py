from common import *

c = get_context()
items, data = c["items"], c["item_data"]
m = data["metrics"]
hero("Home", "What needs your attention today")

urgent = items[items.status.isin(["Out of stock", "Order now"])]
reorder = items[items.status == "Reorder soon"]
over = items[items.status == "Overstock"]

k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Order now", f"{len(urgent)}", f"of {len(items):,} products", RED if len(urgent) else GREEN, RED if len(urgent) else GREEN), unsafe_allow_html=True)
k2.markdown(kpi("Sales at risk", f"${items.sales_at_risk.sum():,.0f}", "if nothing is ordered", YELLOW), unsafe_allow_html=True)
k3.markdown(kpi("Reorder soon", f"{len(reorder)}", "below their reorder point", YELLOW), unsafe_allow_html=True)
k4.markdown(kpi("Overstock", f"${over.excess_value.sum():,.0f}", f"{len(over)} products", BLUE), unsafe_allow_html=True)

if len(urgent):
    t = urgent.iloc[0]
    where = f" at {t.store_id}" if scope_store() is None else ""
    runs = f", running out around {t.runs_out_on:%d %b}" if pd.notna(t.runs_out_on) else ""
    msg = (f"<b>{len(urgent)} product(s)</b> will not last until a new order arrives. The biggest risk is "
           f"<b>{t.item_id}</b>{where}: {t.stock_on_hand:,.0f} on hand against about {t.avg_daily_fc:,.1f} sold per day{runs}. "
           f"Suggested order: <b>{t.suggested_order:,.0f}</b> units.")
else:
    msg = "No product is at risk of running out before the next delivery. Review the reorder list below."
st.markdown(f'<div class="callout">{msg}</div>', unsafe_allow_html=True)

n_up = int((items.stock_source == "uploaded").sum())
sim_note = ("Stock counts are <b>simulated</b> for this demo. Upload your real counts on the Stock monitor page."
            if n_up == 0 else f"Using <b>{n_up}</b> uploaded stock counts; the rest are simulated.")
st.markdown(
    f'<div class="note">Stock position as of <b>{m["data_end"]}</b> · forecasts for <b>{m["forecast_start"]}</b> to '
    f'<b>{m["forecast_end"]}</b> · {sim_note}</div>', unsafe_allow_html=True)

st.markdown("### Priority list")
st.caption("Most urgent first. Suggested order brings stock up to cover the lead time, one order cycle and the safety stock.")
focus = urgent if len(urgent) else reorder
st.markdown(items_table_html(focus.head(10), show_store=scope_store() is None), unsafe_allow_html=True)
if len(focus) > 10:
    st.caption(f"Showing 10 of {len(focus)}. See the Stock monitor for the full list.")

a, b = st.columns(2)
group = "store_id" if scope_store() is None else "dept_id"
with a:
    st.markdown(f"### Stock status by {'store' if group == 'store_id' else 'department'}")
    counts = items.groupby([group, "status"], observed=True).size().unstack(fill_value=0).reindex(columns=STATUS_ORDER, fill_value=0)
    fig = go.Figure()
    for s in STATUS_ORDER:
        fig.add_trace(go.Bar(x=counts.index, y=counts[s], name=STATUS_STYLE[s][0], marker=dict(color=STATUS_STYLE[s][2], line=dict(color="#FFFFFF", width=2))))
    fig.update_layout(barmode="stack")
    show(style_fig(fig, 340))
with b:
    st.markdown("### Sales at risk by category")
    risk = items.groupby("cat_id").sales_at_risk.sum().reindex(["FOODS", "HOBBIES", "HOUSEHOLD"]).fillna(0)
    fig = go.Figure(go.Bar(x=risk.index, y=risk.values, marker_color=[CAT_COLORS[k] for k in risk.index],
                           text=[f"${v:,.0f}" for v in risk.values], textposition="outside"))
    show(style_fig(fig, 340))
    st.caption("Expected lost sales over the supplier lead time if nothing is ordered.")
