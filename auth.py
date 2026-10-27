"""Simple demo sign-in with hashed passwords and two roles (owner, store manager).

This is application-level login for a demo. For a real deployment put the app behind a proper
identity provider (for example Streamlit's built-in OIDC login) and keep user data out of the repo.
"""
import hashlib
import hmac
import json
import os
import time

import streamlit as st

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
ITERATIONS = 200_000
MAX_ATTEMPTS, LOCK_SECONDS = 5, 30


def hash_password(password, salt_hex=None):
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def _load_users():
    with open(USERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def verify(username, password):
    """Return the user record (without secrets) if the credentials are right, else None."""
    u = _load_users().get(username.strip().lower())
    # always do the hashing work so the response time does not reveal whether the user exists
    salt = u["salt"] if u else "00" * 16
    _, digest = hash_password(password, salt)
    if u and hmac.compare_digest(digest, u["hash"]):
        return {"username": username.strip().lower(), "name": u["name"], "role": u["role"], "store": u.get("store")}
    return None


def current_user():
    return st.session_state.get("user")


def logout():
    for k in ("user", "chat", "stock_override", "chat_count"):
        st.session_state.pop(k, None)
    st.rerun()


def login_page():
    """Draw the sign-in screen. Sets session_state['user'] and reruns on success."""
    st.markdown(
        '<div class="login-hero"><div class="login-logo">🛒</div>'
        '<div class="login-title">Retail Intelligence Platform</div>'
        '<div class="login-sub">Know what to order, before you run out.</div></div>',
        unsafe_allow_html=True,
    )
    left, mid, right = st.columns([1, 1.15, 1])
    with mid:
        locked_until = st.session_state.get("locked_until", 0)
        with st.form("login", clear_on_submit=False):
            st.markdown("#### Sign in")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", use_container_width=True)
        if go:
            if time.time() < locked_until:
                st.error(f"Too many attempts. Try again in {int(locked_until - time.time())} seconds.")
            else:
                user = verify(username or "", password or "")
                if user:
                    st.session_state.pop("failed", None)
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.session_state["failed"] = st.session_state.get("failed", 0) + 1
                    if st.session_state["failed"] >= MAX_ATTEMPTS:
                        st.session_state["locked_until"] = time.time() + LOCK_SECONDS
                        st.session_state["failed"] = 0
                    st.error("That username or password is not right.")
        with st.expander("Demo accounts (for this project demo)"):
            st.markdown(
                "| Username | Password | Can see |\n|---|---|---|\n"
                "| `owner` | `Owner@2026` | All stores and company reports |\n"
                "| `manager_ca1` | `Store@CA1` | Store CA_1 only |\n"
                "| `manager_tx2` | `Store@TX2` | Store TX_2 only |"
            )
        st.caption("Demo sign-in only. A live deployment should use a real identity provider.")
