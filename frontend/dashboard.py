"""PromptForge Streamlit dashboard.

Run from the repo root with:
    streamlit run frontend/dashboard.py

Set PROMPTFORGE_API_URL to point at a non-default backend host.
"""
import os
import sys
from pathlib import Path

import streamlit as st

# Allow `from frontend.* import ...` when launched as `streamlit run frontend/dashboard.py`
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from frontend.api.client import APIClient, AuthExpired  # noqa: E402
from frontend.utils.auth import _ensure_state_keys, current_user, logout, require_auth  # noqa: E402
from frontend.views import ab_testing, analytics, developer, reviewer, workspace  # noqa: E402


TABS_BY_ROLE = {
    "admin":     [("Workspace", workspace), ("Developer", developer), ("Reviewer", reviewer), ("Analytics", analytics), ("A/B Testing", ab_testing)],
    "developer": [("Workspace", workspace), ("Developer", developer), ("Analytics", analytics), ("A/B Testing", ab_testing)],
    "reviewer":  [("Workspace", workspace), ("Reviewer", reviewer), ("Analytics", analytics)],
    "analyst":   [("Workspace", workspace), ("Analytics", analytics)],
}


def _build_api() -> APIClient:
    base = os.getenv("PROMPTFORGE_API_URL", "http://localhost:8000")
    api = APIClient(base_url=base, token=st.session_state.get("token"))
    return api


def _sidebar(user: dict | None):
    with st.sidebar:
        st.title("PromptForge")
        st.caption("Prompt mgmt + evaluation")
        if user:
            st.markdown(f"**Signed in as** `{user.get('user_id', '?')}`")
            st.markdown(f"**Role:** `{user.get('role', '?')}`")
            st.markdown(f"**Workspace:** `{user.get('workspace_id', '?')}`")
            st.markdown(f"**Tenant:** `{str(user.get('tenant_id', '?'))[:8]}…`")
            st.divider()
            if st.button("Logout", use_container_width=True):
                logout()
        st.divider()
        st.caption(f"API: {os.getenv('PROMPTFORGE_API_URL', 'http://localhost:8000')}")


def main():
    st.set_page_config(page_title="PromptForge", layout="wide", page_icon="🛠")
    _ensure_state_keys()

    api = _build_api()
    user = current_user()
    _sidebar(user)

    if not user:
        require_auth(api)
        return

    role = user.get("role", "developer")
    tab_specs = TABS_BY_ROLE.get(role, TABS_BY_ROLE["developer"])

    st.markdown(f"### Role: `{role}`")
    tabs = st.tabs([name for name, _ in tab_specs])
    try:
        for tab, (_, mod) in zip(tabs, tab_specs):
            with tab:
                mod.render(api)
    except AuthExpired:
        st.error("Your session expired. Please sign in again.")
        logout()


if __name__ == "__main__":
    main()
