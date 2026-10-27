"""Tools and chat logic for the stock assistant.

No Streamlit imports here, so it can be tested on its own. Access rules (a store manager only sees
their own store) are enforced inside the tool functions, not in the prompt.
"""
import json
import re

import numpy as np
import pandas as pd

MAX_ROWS = 25
VALID_STATUS = ["Out of stock", "Order now", "Reorder soon", "Healthy", "Overstock"]
SORTS = {"sales_at_risk": False, "days_cover": True, "suggested_order": False,
         "stockout_risk": False, "stock_value": False, "excess_value": False}
CATEGORIES = ["FOODS", "HOBBIES", "HOUSEHOLD"]

ITEM_RE = re.compile(r"\b((?:FOODS|HOBBIES|HOUSEHOLD)_\d_\d{3})\b", re.I)
DEPT_RE = re.compile(r"\b((?:FOODS|HOBBIES|HOUSEHOLD)_\d)\b(?!_)", re.I)
STORE_RE = re.compile(r"\b((?:CA|TX|WI)_\d)\b", re.I)


class StockTools:
    def __init__(self, items, data, settings=None, store_scope=None):
        self.items, self.data, self.scope = items, data, store_scope
        self.settings = settings or {}
        self.stores = sorted(items.store_id.unique())
        m = data["metrics"]
        self.as_of, self.f_start, self.f_end = m["data_end"], m["forecast_start"], m["forecast_end"]

    # ---------- helpers ----------
    def _store(self, store):
        if store in (None, "", "all", "All", "All stores"):
            store = None
        else:
            store = str(store).upper()
        if self.scope:
            if store and store != self.scope:
                return None, f"You only have access to store {self.scope}."
            return self.scope, None
        if store and store not in self.stores:
            return None, f"Unknown store '{store}'. Stores are: {', '.join(self.stores)}."
        return store, None

    def _filter(self, store=None, category=None, department=None, status=None):
        df = self.items
        if store:
            df = df[df.store_id == store]
        if category:
            df = df[df.cat_id == str(category).upper()]
        if department:
            df = df[df.dept_id == str(department).upper()]
        if status:
            status = [status] if isinstance(status, str) else list(status)
            df = df[df.status.astype(str).isin(status)]
        return df

    @staticmethod
    def _row(r):
        return {
            "item_id": r.item_id, "store_id": r.store_id, "category": r.cat_id, "department": r.dept_id,
            "status": str(r.status), "stock_on_hand": int(round(r.stock_on_hand)),
            "days_cover": None if r.days_cover >= 99 else round(float(r.days_cover), 1),
            "runs_out_on": None if pd.isna(r.runs_out_on) else str(r.runs_out_on.date()),
            "suggested_order": int(r.suggested_order), "stockout_risk_pct": int(round(r.stockout_risk * 100)),
            "sales_at_risk_usd": round(float(r.sales_at_risk), 2), "reorder_point": int(round(r.reorder_point)),
            "forecast_per_day": round(float(r.avg_daily_fc), 1), "stock_source": r.stock_source,
        }

    # ---------- tools ----------
    def stock_summary(self, store=None):
        store, err = self._store(store)
        if err:
            return {"error": err}
        df = self._filter(store)
        counts = df.status.astype(str).value_counts().reindex(VALID_STATUS, fill_value=0)
        return {
            "scope": store or "all stores", "stock_as_of": self.as_of,
            "forecast_window": [self.f_start, self.f_end], "planning_settings": self.settings,
            "products_tracked": int(len(df)), "status_counts": {k: int(v) for k, v in counts.items()},
            "products_to_order_now": int(counts["Out of stock"] + counts["Order now"]),
            "sales_at_risk_usd": round(float(df.sales_at_risk.sum()), 2),
            "overstock_value_usd": round(float(df.excess_value.sum()), 2),
            "stock_source_counts": {k: int(v) for k, v in df.stock_source.value_counts().items()},
            "top_3_risks": [self._row(r) for r in df.head(3).itertuples()],
        }

    def list_items(self, status=None, store=None, category=None, department=None, sort_by="sales_at_risk", limit=10):
        store, err = self._store(store)
        if err:
            return {"error": err}
        if sort_by not in SORTS:
            sort_by = "sales_at_risk"
        limit = max(1, min(int(limit or 10), MAX_ROWS))
        df = self._filter(store, category, department, status)
        total = len(df)
        df = df.sort_values(sort_by, ascending=SORTS[sort_by]).head(limit)
        return {"total_matching": int(total), "shown": int(len(df)), "sorted_by": sort_by,
                "rows": [self._row(r) for r in df.itertuples()]}

    def item_details(self, item_id, store=None):
        store, err = self._store(store)
        if err:
            return {"error": err}
        item_id = str(item_id).upper()
        df = self._filter(store)
        df = df[df.item_id == item_id]
        if df.empty:
            return {"error": f"No product '{item_id}' found in your scope. Product codes look like FOODS_3_090."}
        rows = []
        for r in df.sort_values("sales_at_risk", ascending=False).head(MAX_ROWS).itertuples():
            d = self._row(r)
            d.update({
                "price_usd": round(float(r.price), 2), "forecast_next_7_days": round(float(r.fc_7d), 1),
                "forecast_next_28_days": round(float(r.fc_28d), 1), "safety_stock": int(round(r.safety_stock)),
                "order_up_to_level": int(round(r.order_up_to)), "demand_during_lead_time": round(float(r.lead_demand), 1),
                "snap_days_next_28": int(r.snap_days_28), "event_days_next_28": int(r.event_days_28),
                "discounted_price_days_next_28": int(r.promo_days_28),
            })
            rows.append(d)
        return {"item_id": item_id, "stores_shown": len(rows), "rows": rows}

    def compare_stores(self):
        if self.scope:
            return {"error": f"You only have access to store {self.scope}, so there is nothing to compare."}
        g = self.items.groupby("store_id")
        out = []
        for s, df in g:
            st_ = df.status.astype(str)
            out.append({"store_id": s, "order_now_or_out": int(st_.isin(["Out of stock", "Order now"]).sum()),
                        "reorder_soon": int((st_ == "Reorder soon").sum()), "overstock": int((st_ == "Overstock").sum()),
                        "sales_at_risk_usd": round(float(df.sales_at_risk.sum()), 2),
                        "suggested_order_units": int(df.suggested_order.sum())})
        out.sort(key=lambda r: (-r["order_now_or_out"], -r["sales_at_risk_usd"]))
        return {"stores": out}

    def demand_outlook(self, store=None, category=None, department=None):
        store, err = self._store(store)
        if err:
            return {"error": err}
        df = self._filter(store, category, department)
        if df.empty:
            return {"error": "No products match that selection."}
        F = self.data["fc_mat"][df.pos.values]
        price = df.price.values
        last28 = float((self.data["meta"].avg_sales_28.values[df.pos.values] * 28).sum())
        n7, n28 = float(F[:, :7].sum()), float(F.sum())
        return {
            "scope": {"store": store or "all stores", "category": category, "department": department},
            "forecast_next_7_days_units": round(n7), "forecast_next_28_days_units": round(n28),
            "forecast_next_28_days_sales_usd": round(float((F.sum(axis=1) * price).sum())),
            "last_28_days_units": round(last28),
            "change_vs_last_28_days_pct": round((n28 / last28 - 1) * 100, 1) if last28 > 0 else None,
        }

    def explain_forecast(self, item_id, store=None):
        store, err = self._store(store)
        if err:
            return {"error": err}
        item_id = str(item_id).upper()
        df = self._filter(store)
        df = df[df.item_id == item_id]
        if df.empty:
            return {"error": f"No product '{item_id}' found in your scope."}
        pos = df.pos.values
        adj = {k: round(float(self.data["adj"][k][pos].mean()), 1) for k in self.data["adj"]}
        imp = self.data["importance"].groupby("group").gain_pct.sum().round(1).to_dict()
        fac = self.data["factors"]
        lifts = {f"{r.factor}: {r.level}": round(float(r.lift_pct), 1) for r in fac.itertuples()}
        return {
            "item_id": item_id, "stores_included": sorted(df.store_id.unique()),
            "average_effect_on_forecast_pct_next_28_days": {
                "day_of_week_and_calendar": adj["adj_calendar"], "snap_days_and_events": adj["adj_snap_events"],
                "price_and_promotions": adj["adj_price_promo"]},
            "snap_days_next_28": int(df.snap_days_28.mean()), "event_days_next_28": int(df.event_days_28.mean()),
            "discounted_price_days_next_28": int(df.promo_days_28.sum()),
            "model_weight_by_factor_group_pct": imp,
            "typical_sales_lift_vs_normal_pct_all_products": lifts,
            "note": "Recent sales level drives most of the forecast; the other factors adjust it.",
        }

    def run(self, name, args):
        fn = {"stock_summary": self.stock_summary, "list_items": self.list_items, "item_details": self.item_details,
              "compare_stores": self.compare_stores, "demand_outlook": self.demand_outlook,
              "explain_forecast": self.explain_forecast}.get(name)
        if fn is None:
            return {"error": f"Unknown tool {name}"}
        try:
            return fn(**(args or {}))
        except TypeError as e:
            return {"error": f"Bad arguments for {name}: {e}"}
        except Exception as e:  # never let a tool crash the chat
            return {"error": f"{type(e).__name__}: {e}"}


STORE_PROP = {"type": "string", "description": "Store code such as CA_1. Omit for all stores you can access."}
TOOL_SPECS = [
    {"name": "stock_summary", "description": "Overview of stock health: counts per status, products to order now, sales at risk, overstock value, and the top 3 risks.",
     "input_schema": {"type": "object", "properties": {"store": STORE_PROP}}},
    {"name": "list_items", "description": "List products (item x store rows) filtered by status, store, category or department, sorted by a metric. Use this for 'what should I order', 'what is running out', 'what is overstocked'.",
     "input_schema": {"type": "object", "properties": {
         "status": {"type": "array", "items": {"type": "string", "enum": VALID_STATUS}, "description": "Statuses to include."},
         "store": STORE_PROP, "category": {"type": "string", "enum": CATEGORIES},
         "department": {"type": "string", "description": "Department code such as FOODS_3."},
         "sort_by": {"type": "string", "enum": list(SORTS), "description": "Default sales_at_risk. days_cover sorts lowest first."},
         "limit": {"type": "integer", "description": f"Rows to return, up to {MAX_ROWS}."}}}},
    {"name": "item_details", "description": "Full stock, forecast and ordering details for one product code, in one store or all stores.",
     "input_schema": {"type": "object", "properties": {"item_id": {"type": "string", "description": "Product code such as FOODS_3_090."}, "store": STORE_PROP}, "required": ["item_id"]}},
    {"name": "compare_stores", "description": "Compare all stores on products to order, overstock and sales at risk. Owners only.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "demand_outlook", "description": "Forecast units and sales value for the next 7 and 28 days compared with the last 28 days, for a store, category or department.",
     "input_schema": {"type": "object", "properties": {"store": STORE_PROP, "category": {"type": "string", "enum": CATEGORIES}, "department": {"type": "string"}}}},
    {"name": "explain_forecast", "description": "Explain what drives a product's forecast: weekday pattern, SNAP days, events, price, and how much weight the model gives each factor.",
     "input_schema": {"type": "object", "properties": {"item_id": {"type": "string"}, "store": STORE_PROP}, "required": ["item_id"]}},
]


def system_prompt(tools, user_name="the user"):
    scope = f"store {tools.scope} only" if tools.scope else "all stores"
    return (
        f"You are the stock assistant inside a retail planning platform, helping {user_name} ({scope}). "
        "Answer only from tool results; never invent numbers, products or dates. If the tools cannot answer, say so plainly. "
        "Lead with the answer, then a short list or table. Use plain language for a busy store owner. "
        f"Stock position is as of {tools.as_of}; forecasts cover {tools.f_start} to {tools.f_end}. "
        "Stock counts are simulated unless a row says stock_source is 'uploaded'; mention this when it affects a decision. "
        "Suggested orders assume no open orders and cannot be placed from here. Dollar amounts are expected lost sales. "
        "days_cover of null means more than 99 days. Keep replies under about 200 words."
    )


def ask_llm(client, model, tools, question, history, user_name="the user", max_steps=6):
    """Run the tool-use loop with the Anthropic Messages API. `client` is anthropic.Anthropic (or a test double)."""
    messages = [{"role": m["role"], "content": m["content"]} for m in history] + [{"role": "user", "content": question}]
    system = system_prompt(tools, user_name)
    for _ in range(max_steps):
        resp = client.messages.create(model=model, max_tokens=900, system=system, tools=TOOL_SPECS, messages=messages)
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = tools.run(block.name, dict(block.input))
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, default=str)})
            messages.append({"role": "user", "content": results})
            continue
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        return text or "I could not produce an answer. Please try rephrasing."
    return "That question needed too many steps. Please ask something narrower."


# ---------- built-in (no API key) assistant ----------
def _table(rows, cols):
    head = "| " + " | ".join(h for _, h in cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for r in rows:
        cells = []
        for k, _ in cols:
            v = r.get(k)
            cells.append("-" if v is None else (f"${v:,.0f}" if k.endswith("_usd") else (f"{v:,}" if isinstance(v, int) else str(v))))
        body += "| " + " | ".join(cells) + " |\n"
    return head + body


LIST_COLS = [("item_id", "Product"), ("store_id", "Store"), ("status", "Status"), ("stock_on_hand", "On hand"),
             ("days_cover", "Days of cover"), ("runs_out_on", "Runs out"), ("suggested_order", "Order"), ("sales_at_risk_usd", "Sales at risk")]

HELP = (
    "I can answer questions about your stock from the data. Try:\n"
    "- *How are we doing today?*\n- *What should I order?*\n- *What is running out?*\n- *What is overstocked?*\n"
    "- *Tell me about FOODS_3_090* or *Why is FOODS_3_090 forecast to sell that much?*\n"
    "- *How much will we sell next week?* (add a category, store or department to narrow it)\n"
    "- *Compare stores* (owners only)"
)


def answer_rule_based(question, tools):
    q = question.lower()
    sm = STORE_RE.search(question)
    store = sm.group(1).upper() if sm else None
    cat = next((c for c in CATEGORIES if re.search(rf"\b{c.lower()}\b", q) and not ITEM_RE.search(question) and not DEPT_RE.search(question)), None)
    dept_m = DEPT_RE.search(question) if not ITEM_RE.search(question) else None
    dept = dept_m.group(1).upper() if dept_m else None
    item_m = ITEM_RE.search(question)
    has = lambda *w: any(x in q for x in w)

    if item_m:
        item = item_m.group(1).upper()
        if has("why", "driver", "explain", "factor", "reason", "affect", "forecast to"):
            r = tools.explain_forecast(item, store)
            if "error" in r:
                return r["error"]
            a = r["average_effect_on_forecast_pct_next_28_days"]
            return (f"**{item}** ({', '.join(r['stores_included'])}). Most of the forecast comes from recent sales; other factors adjust it.\n"
                    f"- Day of week and calendar: {a['day_of_week_and_calendar']:+.1f}% on average\n"
                    f"- SNAP days and events: {a['snap_days_and_events']:+.1f}% ({r['snap_days_next_28']} SNAP days, {r['event_days_next_28']} event days in the next 28)\n"
                    f"- Price and promotions: {a['price_and_promotions']:+.1f}% ({r['discounted_price_days_next_28']} discounted day(s))\n"
                    f"- Model weight: {r['model_weight_by_factor_group_pct'].get('recent_demand', 0):.0f}% recent sales, "
                    f"{r['model_weight_by_factor_group_pct'].get('calendar', 0):.0f}% calendar, "
                    f"{r['model_weight_by_factor_group_pct'].get('price_promo', 0):.1f}% price.\n"
                    "Across all products, weekends sell about 16 to 20% more than an average day.")
        r = tools.item_details(item, store)
        if "error" in r:
            return r["error"]
        lines = [f"**{item}**"]
        for d in r["rows"][:6]:
            runs = f", runs out around {d['runs_out_on']}" if d["runs_out_on"] else ""
            lines.append(f"- **{d['store_id']}**: {d['status']}. {d['stock_on_hand']} on hand, about {d['forecast_per_day']} sold per day"
                         f"{runs}. Reorder point {d['reorder_point']}; suggested order **{d['suggested_order']}** units.")
        if r["stores_shown"] > 6:
            lines.append(f"...and {r['stores_shown'] - 6} more stores.")
        return "\n".join(lines)

    if has("compare", "which store", "best store", "worst store", "by store", "per store", "each store"):
        r = tools.compare_stores()
        if "error" in r:
            return r["error"]
        return "Stores ranked by products that need ordering:\n\n" + _table(r["stores"], [
            ("store_id", "Store"), ("order_now_or_out", "Order now / out"), ("reorder_soon", "Reorder soon"),
            ("overstock", "Overstock"), ("sales_at_risk_usd", "Sales at risk")])

    if has("sell", "demand", "forecast", "next week", "next month", "expect") and not has("order"):
        r = tools.demand_outlook(store, cat, dept)
        if "error" in r:
            return r["error"]
        ch = f" ({r['change_vs_last_28_days_pct']:+.1f}% vs the last 28 days)" if r["change_vs_last_28_days_pct"] is not None else ""
        return (f"Forecast for {r['scope']['store']}{(' · ' + (dept or cat)) if (dept or cat) else ''}:\n"
                f"- Next 7 days: **{r['forecast_next_7_days_units']:,} units**\n"
                f"- Next 28 days: **{r['forecast_next_28_days_units']:,} units**, about ${r['forecast_next_28_days_sales_usd']:,} in sales{ch}")

    if has("overstock", "excess", "too much", "surplus", "dead stock"):
        r = tools.list_items(["Overstock"], store, cat, dept, "excess_value", 10)
        if "error" in r:
            return r["error"]
        if not r["rows"]:
            return "No overstocked products right now."
        return f"{r['total_matching']} products have more stock than needed. The biggest:\n\n" + _table(r["rows"], LIST_COLS[:6])

    if has("out of stock", "stockout", "stock-out", "run out", "running out", "ran out", "sold out", "urgent", "critical", "at risk", "running low", "low stock"):
        r = tools.list_items(["Out of stock", "Order now"], store, cat, dept, "sales_at_risk", 10)
        if "error" in r:
            return r["error"]
        if not r["rows"]:
            return "Nothing is at risk of running out before the next delivery."
        return f"{r['total_matching']} products will not last until a new order arrives. The most urgent:\n\n" + _table(r["rows"], LIST_COLS) + "\nOrder quantities assume no open orders."

    if has("order", "reorder", "restock", "buy", "purchase", "replenish", "what should i"):
        r = tools.list_items(["Out of stock", "Order now", "Reorder soon"], store, cat, dept, "sales_at_risk", 10)
        if "error" in r:
            return r["error"]
        if not r["rows"]:
            return "No orders are needed right now."
        return f"{r['total_matching']} products are at or below their reorder point. Highest priority first:\n\n" + _table(r["rows"], LIST_COLS) + "\nOrder quantities assume no open orders."

    if has("summary", "overview", "status", "how are we", "how am i", "how is", "today", "attention", "doing", "health"):
        r = tools.stock_summary(store)
        if "error" in r:
            return r["error"]
        c = r["status_counts"]
        txt = (f"**{r['scope'].capitalize()}**, stock as of {r['stock_as_of']}.\n"
               f"- {r['products_tracked']:,} products tracked: {c['Healthy']} healthy, {c['Reorder soon']} to reorder soon, "
               f"**{r['products_to_order_now']} to order now**, {c['Overstock']} overstocked.\n"
               f"- Expected lost sales if nothing is ordered: **${r['sales_at_risk_usd']:,.0f}**.\n")
        if r["top_3_risks"]:
            txt += "\nMost urgent:\n\n" + _table(r["top_3_risks"], LIST_COLS)
        return txt

    return HELP
