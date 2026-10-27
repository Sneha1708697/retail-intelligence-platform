from common import *

c = get_context()
hero("Alerts", "Stores that need attention")
healthy = len(c["inv"]) - len(set(c["stockout"]) | set(c["overstock"]))

a, b, d = st.columns(3)
a.markdown(kpi("Stockout alerts", f"{len(c['stockout'])}", "above 5% target", RED, RED if c["stockout"] else GREEN), unsafe_allow_html=True)
b.markdown(kpi("Overstock alerts", f"{len(c['overstock'])}", "excess buffer stock", YELLOW), unsafe_allow_html=True)
d.markdown(kpi("Healthy stores", f"{healthy}", f"of {len(c['inv'])}", GREEN, GREEN), unsafe_allow_html=True)

st.markdown("### Stockout risk")
if c["stockout"]:
    for _, r in c["stockout_df"].iterrows():
        st.markdown(
            f'<div class="alert-card" style="border-left-color:{RED}"><div class="alert-title">{r["store"]} · stockout rate {r["stockout_rate"]:.1%}</div>'
            f'<div class="alert-body">Above the {TARGET_STOCKOUT_RATE:.0%} target. Consider a higher service level or more safety stock.</div></div>',
            unsafe_allow_html=True)
else:
    st.success("No stores exceed the stockout target.")

st.markdown("### Overstock")
if c["overstock"]:
    for s in c["overstock"]:
        st.markdown(
            f'<div class="alert-card" style="border-left-color:{YELLOW}"><div class="alert-title">{s} · reorder point {c["ratio"][s]:.1f}× daily demand</div>'
            f'<div class="alert-body">Buffer is high compared with other stores. Review lead time and holding cost assumptions.</div></div>',
            unsafe_allow_html=True)
else:
    st.success("No stores flagged for excess inventory.")
