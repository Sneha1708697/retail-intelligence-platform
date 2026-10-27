from common import *

c = get_context()
hero("Categories", "Product categories and the departments inside them")
cat = st.selectbox("Category", c["category"].columns.tolist())
y = c["category"][cat]
share = y.sum() / c["category"].sum().sum()
depts = [d for d in c["dept"].columns if d.startswith(cat + "_")]

k1, k2, k3 = st.columns(3)
k1.markdown(kpi("Share of total sales", f"{share:.1%}", cat, BLUE), unsafe_allow_html=True)
k2.markdown(kpi("Avg daily units", f"{y.mean():,.0f}", "all stores", YELLOW), unsafe_allow_html=True)
k3.markdown(kpi("Departments", f"{len(depts)}", ", ".join(depts), BLUE), unsafe_allow_html=True)

st.markdown("### Category demand")
fig = go.Figure()
fig.add_trace(go.Scatter(x=y.index, y=y, name="Daily", line=dict(color=SKY, width=1)))
fig.add_trace(go.Scatter(x=y.index, y=y.rolling(28).mean(), name="28-day average", line=dict(color=BLUE, width=2.5)))
show(style_fig(fig, 320))

a, b = st.columns([2, 1])
with a:
    st.markdown("### Departments (28-day average)")
    fig = go.Figure()
    for d, color in zip(depts, [BLUE, YELLOW, SKY]):
        fig.add_trace(go.Scatter(x=c["dept"].index, y=c["dept"][d].rolling(28).mean(), name=d, line=dict(color=color, width=2)))
    show(style_fig(fig, 320))
with b:
    st.markdown("### Department share")
    tot = c["dept"][depts].sum()
    show(style_fig(go.Figure(go.Pie(labels=tot.index, values=tot.values, hole=0.58,
                                    marker=dict(colors=[BLUE, YELLOW, SKY], line=dict(color="#FFFFFF", width=2)))), 320))
