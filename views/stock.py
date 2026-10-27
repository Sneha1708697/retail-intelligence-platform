from common import *

c = get_context()
items = c["items"]
hero("Stock monitor", "Every product in every store: how much is left, when it runs out, and what to order")

# ---------- filters ----------
f1, f2, f3, f4 = st.columns(4)
if scope_store() is None:
    store = f1.selectbox("Store", ["All stores"] + sorted(items.store_id.unique()))
else:
    store = f1.selectbox("Store", [scope_store()], disabled=True)
cat = f2.selectbox("Category", ["All"] + sorted(items.cat_id.unique()))
dept_pool = items if cat == "All" else items[items.cat_id == cat]
dept = f3.selectbox("Department", ["All"] + sorted(dept_pool.dept_id.unique()))
default_status = ["Out of stock", "Order now", "Reorder soon"]
status = f4.multiselect("Status", STATUS_ORDER, default=default_status)
search = st.text_input("Find a product", placeholder="Type part of a product code, e.g. FOODS_3_090")

view = items
if store != "All stores":
    view = view[view.store_id == store]
if cat != "All":
    view = view[view.cat_id == cat]
if dept != "All":
    view = view[view.dept_id == dept]
if status:
    view = view[view.status.isin(status)]
if search.strip():
    view = view[view.item_id.str.contains(search.strip(), case=False, regex=False)]

# ---------- counts ----------
base = items if store == "All stores" else items[items.store_id == store]
cols = st.columns(len(STATUS_ORDER))
for col, s in zip(cols, STATUS_ORDER):
    col.markdown(kpi(STATUS_STYLE[s][0], f"{int((base.status == s).sum())}", "products", STATUS_STYLE[s][2]), unsafe_allow_html=True)

st.markdown(f"### {len(view):,} products shown")
show_cols = {
    "item_id": "Product", "store_id": "Store", "cat_id": "Category", "dept_id": "Department", "status": "Status",
    "stock_on_hand": "On hand", "days_cover": "Days of cover", "runs_out_on": "Runs out on",
    "suggested_order": "Suggested order", "sales_at_risk": "Sales at risk ($)", "stockout_risk": "Stockout risk",
    "reorder_point": "Reorder point", "safety_stock": "Safety stock", "avg_daily_fc": "Forecast per day",
    "stock_source": "Stock source",
}
table = view[list(show_cols)].rename(columns=show_cols).copy()
table["Status"] = table["Status"].astype(str).map(lambda s: STATUS_STYLE[s][0])
table["Stockout risk"] = (table["Stockout risk"] * 100).round(0)
for col in ["On hand", "Days of cover", "Suggested order", "Sales at risk ($)", "Reorder point", "Safety stock", "Forecast per day"]:
    table[col] = table[col].round(1)
table["Runs out on"] = pd.to_datetime(table["Runs out on"]).dt.date
cfg = {
    "Days of cover": st.column_config.NumberColumn(format="%.1f", help="On hand divided by the average daily forecast (99 = more than 99 days)."),
    "Sales at risk ($)": st.column_config.NumberColumn(format="$%.0f"),
    "Stockout risk": st.column_config.NumberColumn(format="%.0f%%", help="Chance demand during the lead time exceeds what is on hand."),
    "Runs out on": st.column_config.DateColumn(format="DD MMM", help="Blank means the stock lasts beyond the 28-day forecast."),
}
if scope_store():
    table = table.drop(columns=["Store"])
try:
    st.dataframe(table, hide_index=True, column_config=cfg, width="stretch")
except Exception:
    st.dataframe(table, hide_index=True, column_config=cfg, use_container_width=True)

orders = view[view.suggested_order > 0][["store_id", "item_id", "cat_id", "dept_id", "stock_on_hand", "suggested_order", "price"]]
d1, d2 = st.columns([1, 3])
d1.download_button("Download order list (CSV)", orders.to_csv(index=False).encode("utf-8"), "order_list.csv", "text/csv",
                   disabled=orders.empty)
d2.caption("The order list contains the products in the table above that need ordering. It assumes no open orders.")

# ---------- real stock counts ----------
st.markdown("### Use your real stock counts")
with st.expander("Upload stock on hand (CSV)", expanded=False):
    st.markdown(
        "The sample data has no real inventory, so starting stock is simulated. To use your own counts, download the "
        "template, replace the `stock_on_hand` numbers, and upload it. Rows for products or stores you cannot see are ignored."
    )
    template = items[["item_id", "store_id", "stock_on_hand"]].sort_values(["store_id", "item_id"])
    st.download_button("Download template", template.to_csv(index=False).encode("utf-8"), "stock_template.csv", "text/csv")
    up = st.file_uploader("Stock file", type="csv")
    if up is not None:
        sig = (up.name, up.size)
        if st.session_state.get("stock_sig") != sig:
            try:
                df = pd.read_csv(up)
                need = {"item_id", "store_id", "stock_on_hand"}
                if not need.issubset(df.columns):
                    st.error(f"The file needs these columns: {', '.join(sorted(need))}.")
                else:
                    df["stock_on_hand"] = pd.to_numeric(df["stock_on_hand"], errors="coerce")
                    df = df.dropna(subset=["stock_on_hand"])
                    df = df[df.stock_on_hand >= 0]
                    known = set(zip(c["item_data"]["meta"].item_id, c["item_data"]["meta"].store_id))
                    ok = df[[(i, s) in known and (scope_store() in (None, s)) for i, s in zip(df.item_id, df.store_id)]]
                    st.session_state["stock_override"] = ok[["item_id", "store_id", "stock_on_hand"]]
                    st.session_state["stock_sig"] = sig
                    st.success(f"Loaded {len(ok):,} stock counts. {len(df) - len(ok):,} rows were ignored.")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not read that file: {e}")
    if st.session_state.get("stock_override") is not None:
        st.info(f"{len(st.session_state['stock_override']):,} uploaded counts are in use.")
        if st.button("Go back to simulated stock"):
            st.session_state.pop("stock_override", None)
            st.session_state.pop("stock_sig", None)
            st.rerun()
