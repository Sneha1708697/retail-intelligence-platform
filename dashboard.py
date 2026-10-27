"""
Retail Intelligence Platform - sign-in, role-based pages, stock monitor and assistant.

Run with:  py -m streamlit run dashboard.py
Needs the hierarchy_output folder and users.json next to this file.
"""
import streamlit as st

st.set_page_config(page_title="Retail Intelligence Platform", layout="wide", page_icon="🛒")

import auth
import common

common.setup()

user = auth.current_user()
if user is None:
    auth.login_page()
    st.stop()

try:
    common.load_data()
    import items as _items
    _items.load_item_data()
except FileNotFoundError as e:
    st.error(f"Couldn't find a required file: {e}. Make sure the `hierarchy_output` folder sits next to dashboard.py.")
    st.stop()

daily = [
    st.Page("views/home.py", title="Home", icon="🏠", default=True),
    st.Page("views/stock.py", title="Stock monitor", icon="📦"),
    st.Page("views/products.py", title="Product explorer", icon="🔎"),
    st.Page("views/assistant.py", title="Stock assistant", icon="💬"),
]
pages = {"Daily work": daily}
if user["role"] == "owner":
    pages["Company view"] = [
        st.Page("views/regions.py", title="Regions", icon="🗺️"),
        st.Page("views/stores.py", title="Stores", icon="🏬"),
        st.Page("views/categories.py", title="Categories", icon="🧺"),
    ]
    pages["Forecasts and policy"] = [
        st.Page("views/forecasting.py", title="Forecast insights", icon="📈"),
        st.Page("views/inventory.py", title="Store policy", icon="⚙️"),
    ]
pg = st.navigation(pages)

with st.sidebar:
    st.divider()
    where = f"Store {user['store']}" if user["store"] else "All stores"
    st.markdown(f'<div class="usercard"><b>{user["name"]}</b><br><span style="color:#6B7280">{where}</span></div>',
                unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        auth.logout()

    st.divider()
    st.markdown("**Planning settings**")
    st.slider("Target service level (%)", 90.0, 99.5, 95.0, 0.5, key="service_level",
              help="Higher means more safety stock and fewer stockouts.")
    st.slider("Supplier lead time (days)", 1, 7, 3, key="lead_time")
    st.slider("Order cycle (days)", 3, 14, 7, key="order_cycle", help="How often you place orders.")
    st.slider("Overstock above (days of cover)", 10, 45, 14, key="overstock_days")
    if user["role"] == "owner":
        with st.expander("Cost assumptions"):
            st.number_input("Ordering cost per order", min_value=1.0, value=50.0, step=5.0, key="ordering_cost")
            st.number_input("Holding cost per unit / year", min_value=0.1, value=2.0, step=0.5, key="holding_cost")

    st.divider()
    ctx = common.get_context()
    urgent = int(ctx["items"].status.isin(["Out of stock", "Order now"]).sum())
    if urgent:
        st.error(f"🔔 {urgent} product(s) need ordering now")
    else:
        st.success("✅ Nothing urgent")

pg.run()
