import streamlit as st

from frontend.api.client import APIClient, APIError


ROLE_OPTIONS = ["developer", "reviewer", "admin"]


def _ensure_state_keys():
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("evaluations", [])
    st.session_state.setdefault("feedback", {})


def current_user() -> dict | None:
    return st.session_state.get("user")


def logout():
    for key in ("token", "user"):
        st.session_state[key] = None
    st.session_state["evaluations"] = []
    st.session_state["feedback"] = {}
    st.rerun()


def login_form(api: APIClient):
    st.subheader("Sign in")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True)
    if not submitted:
        return
    try:
        api.login(username, password)
        user = api.me()
        st.session_state["token"] = api.token
        st.session_state["user"] = user
        st.success(f"Logged in as {user['role']}")
        st.rerun()
    except APIError as e:
        st.error(f"Login failed: {e.message}")


def register_form(api: APIClient):
    st.subheader("Create account")
    with st.form("register_form", clear_on_submit=True):
        username = st.text_input("New username", key="reg_username")
        password = st.text_input("New password", type="password", key="reg_password")
        role = st.selectbox("Role", ROLE_OPTIONS, index=0, key="reg_role")
        submitted = st.form_submit_button("Register", use_container_width=True)
    if not submitted:
        return
    try:
        api.register(username, password, role)
        st.success(f"Account '{username}' created. Sign in below.")
    except APIError as e:
        st.error(f"Registration failed: {e.message}")


def require_auth(api: APIClient) -> dict | None:
    """If unauthenticated, render login + register in the main panel and stop.

    Returns the current user dict if authenticated, otherwise None (and Streamlit
    has already been instructed to halt with st.stop()).
    """
    _ensure_state_keys()

    if st.session_state.get("token"):
        api.token = st.session_state["token"]
        return st.session_state.get("user")

    st.title("PromptForge")
    st.caption("Multi-tenant prompt management & evaluation dashboard")
    left, right = st.columns(2)
    with left:
        login_form(api)
    with right:
        register_form(api)
    st.stop()
    return None
