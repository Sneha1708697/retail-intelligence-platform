import os

import assistant_core as ac
from common import *

c = get_context()
user = get_user()
ss = st.session_state
tools = ac.StockTools(
    c["items"], c["item_data"], store_scope=scope_store(),
    settings={"service_level_pct": ss.get("service_level", 95.0), "lead_time_days": ss.get("lead_time", 3),
              "order_cycle_days": ss.get("order_cycle", 7), "overstock_above_days_cover": ss.get("overstock_days", 14)},
)


def api_key():
    try:
        k = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        k = None
    return k or os.environ.get("ANTHROPIC_API_KEY")


def model_name():
    try:
        m = st.secrets.get("ANTHROPIC_MODEL")
    except Exception:
        m = None
    return m or os.environ.get("ANTHROPIC_MODEL") or "claude-haiku-5-5"


@st.cache_resource
def get_client(key):
    import anthropic
    return anthropic.Anthropic(api_key=key)


key = api_key()
ai_on = False
if key:
    try:
        import anthropic  # noqa: F401
        ai_on = True
    except ImportError:
        ai_on = False

hero("Stock assistant", "Ask about what to order, what is running out and why the forecast looks the way it does")
if ai_on:
    st.markdown(badge("● AI mode: Claude", "green") + "&nbsp; Answers are written by Claude from your stock data.", unsafe_allow_html=True)
else:
    st.markdown(badge("● Built-in mode", "blue") + "&nbsp; Answers come from your stock data using fixed question types.", unsafe_allow_html=True)
st.write("")

MAX_QUESTIONS = 40
chat = ss.setdefault("chat", [])

examples = ["How are we doing today?", "What should I order?", "What is running out?", "What is overstocked?",
            "How much will we sell next week?"]
cols = st.columns(len(examples))
for col, ex in zip(cols, examples):
    if col.button(ex, use_container_width=True):
        ss["pending_q"] = ex

for m in chat:
    with st.chat_message(m["role"], avatar="🧑‍💼" if m["role"] == "user" else "🛒"):
        st.markdown(m["content"])

question = st.chat_input("Ask about your stock, e.g. 'What should I order at " + (scope_store() or "CA_1") + "?'") or ss.pop("pending_q", None)
if question:
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)
    history = [{"role": m["role"], "content": m["content"]} for m in chat[-8:]]
    chat.append({"role": "user", "content": question})
    with st.chat_message("assistant", avatar="🛒"):
        if ss.get("chat_count", 0) >= MAX_QUESTIONS:
            answer = "You have reached the question limit for this session. Sign out and back in to start again."
        else:
            ss["chat_count"] = ss.get("chat_count", 0) + 1
            answer, note = None, ""
            with st.spinner("Checking your stock..."):
                if ai_on:
                    try:
                        answer = ac.ask_llm(get_client(key), model_name(), tools, question, history, user["name"])
                    except Exception as e:
                        note = f"\n\n*The AI service was not available ({type(e).__name__}), so this answer comes from the built-in assistant.*"
                if answer is None:
                    answer = ac.answer_rule_based(question, tools) + note
        st.markdown(answer)
    chat.append({"role": "assistant", "content": answer})

if len(chat):
    if st.button("Clear conversation"):
        ss["chat"] = []
        st.rerun()

if user["role"] == "owner":
    with st.expander("How to turn on the AI mode"):
        st.markdown(
            "- Create an API key in the Anthropic Console.\n"
            "- Add it as a secret named `ANTHROPIC_API_KEY`: in `.streamlit/secrets.toml` when running locally, or in the app's "
            "**Secrets** settings on Streamlit Community Cloud.\n"
            "- Optionally set `ANTHROPIC_MODEL` (the default is `claude-haiku-5-5`, the smallest and cheapest model).\n"
            "- Never upload `secrets.toml` to GitHub. Calls to the API are billed to your account, and each session is limited to 40 questions.\n"
            "- Store managers can only ask about their own store. That limit is enforced in the code, not just in the instructions to the AI."
        )
