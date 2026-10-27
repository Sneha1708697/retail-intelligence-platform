from common import *

c = get_context()
hero("Overview", "Company-wide performance at a glance")

k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Best forecast error (MAE)", f"{c['best_mae']:,.0f}", c["best_name"], BLUE), unsafe_allow_html=True)
k2.markdown(kpi("Error reduction", f"{c['improvement']:.1f}%", "vs direct forecast", GREEN, GREEN), unsafe_allow_html=True)
so = RED if c["avg_stockout"] > TARGET_STOCKOUT_RATE else GREEN
k3.markdown(kpi("Avg stockout rate", f"{c['avg_stockout']:.1%}", f"Target ≤ {TARGET_STOCKOUT_RATE:.0%}", YELLOW, so), unsafe_allow_html=True)
k4.markdown(kpi("Active alerts", f"{c['n_alerts']}", "stockout + overstock", RED if c["n_alerts"] else GREEN), unsafe_allow_html=True)

st.markdown(
    f'<div class="callout"><b>Insight:</b> {c["best_name"]} reconciliation cut forecast error by '
    f'<b>{c["improvement"]:.1f}%</b> versus forecasting the total directly. '
    f'{len(c["stockout"])} store(s) exceeded the {TARGET_STOCKOUT_RATE:.0%} stockout target in the backtest.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([2, 1])
with left:
    st.markdown("### Total demand over time")
    t = c["total"]
    show(style_fig(go.Figure(go.Scatter(x=t.index, y=t.iloc[:, 0], line=dict(color=BLUE, width=1.5),
                                        fill="tozeroy", fillcolor="rgba(0,113,206,0.10)")), 320))
with right:
    st.markdown("### Category mix")
    ct = c["category"].sum().sort_values(ascending=False)
    show(style_fig(go.Figure(go.Pie(labels=ct.index, values=ct.values, hole=0.58,
                                    marker=dict(colors=[BLUE, YELLOW, SKY], line=dict(color="#FFFFFF", width=2)))), 320))

st.markdown("### Store health")
st.markdown(health_table(c), unsafe_allow_html=True)
