from common import *

c = get_context()
hero("Regions", "Company demand split by state, then by store within a state")
state = c["state"]

a, b = st.columns([2, 1])
with a:
    st.markdown("### Daily demand by state")
    fig = go.Figure()
    for col, color in zip(state.columns, [BLUE, YELLOW, SKY]):
        fig.add_trace(go.Scatter(x=state.index, y=state[col], name=col, line=dict(color=color, width=1.3)))
    show(style_fig(fig, 340))
with b:
    st.markdown("### Share of total sales")
    tot = state.sum()
    show(style_fig(go.Figure(go.Pie(labels=tot.index, values=tot.values, hole=0.58,
                                    marker=dict(colors=[BLUE, YELLOW, SKY], line=dict(color="#FFFFFF", width=2)))), 340))

st.markdown("### Stores within a state")
sel = st.selectbox("State", state.columns.tolist())
stores = [s for s in c["store"].columns if s.startswith(sel)]
avg = c["store"][stores].mean()
show(style_fig(go.Figure(go.Bar(x=avg.index, y=avg.values, marker_color=BLUE,
                                text=[f"{v:,.0f}" for v in avg.values], textposition="outside")), 320))
st.caption(f"Average daily units sold per store in {sel}.")
