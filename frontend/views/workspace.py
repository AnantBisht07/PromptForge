import time

import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError


WORKSPACE_ROLES = ["developer", "reviewer", "analyst", "admin"]


def _current_workspace_role(members: list[dict]) -> str:
    user = st.session_state.get("user") or {}
    user_id = user.get("user_id")
    for member in members:
        if member.get("user_id") == user_id:
            return member.get("role", "")
    return ""


def _refresh_controls(key_prefix: str) -> tuple[bool, int]:
    left, right, spacer = st.columns([1, 1, 3])
    if left.button("Refresh", key=f"{key_prefix}_refresh", use_container_width=True):
        st.rerun()
    auto_refresh = right.checkbox("Auto refresh", key=f"{key_prefix}_auto")
    interval = 15
    if auto_refresh:
        interval = int(spacer.number_input(
            "Seconds",
            min_value=5,
            max_value=60,
            value=15,
            step=5,
            key=f"{key_prefix}_interval",
        ))
    return auto_refresh, interval


def _create_workspace(api: APIClient):
    with st.expander("Create workspace", expanded=False):
        with st.form("workspace_create"):
            name = st.text_input("Workspace name", placeholder="Growth AI Team")
            submitted = st.form_submit_button("Create", use_container_width=True)
        if submitted:
            if not name.strip():
                st.warning("Workspace name cannot be empty.")
                return
            try:
                created = api.create_workspace(name.strip())
                st.session_state["user"] = api.me()
                st.success(f"Created workspace #{created['id']}.")
                st.rerun()
            except APIError as e:
                st.error(f"Failed: {e.message}")


def _add_member(api: APIClient, workspace_id: int, role: str):
    if role != "admin":
        return
    with st.expander("Add member", expanded=False):
        with st.form("workspace_add_member"):
            username = st.text_input("Username")
            member_role = st.selectbox("Role", WORKSPACE_ROLES, index=0)
            submitted = st.form_submit_button("Add", use_container_width=True)
        if submitted:
            if not username.strip():
                st.warning("Username cannot be empty.")
                return
            try:
                api.add_member(username=username.strip(), role=member_role, workspace_id=workspace_id)
                st.success(f"Added {username.strip()} as {member_role}.")
                st.rerun()
            except APIError as e:
                st.error(f"Failed: {e.message}")


def _prompt_table(prompts: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": prompt["id"],
            "status": prompt.get("status", "review"),
            "versions": len(prompt.get("versions", [])),
            "created_at": prompt["created_at"][:19],
            "content": prompt["content"][:120],
        }
        for prompt in prompts
    ])


def _approval_queue(api: APIClient, prompts: list[dict], can_review: bool):
    review_prompts = [prompt for prompt in prompts if prompt.get("status") == "review"]
    st.subheader("Approval queue")
    if not review_prompts:
        st.info("No prompts waiting for review.")
        return

    for prompt in review_prompts:
        with st.container(border=True):
            top = st.columns([3, 1])
            top[0].markdown(f"**Prompt #{prompt['id']}**")
            top[1].markdown("`review`")
            st.code(prompt["content"], language="markdown")

            if not can_review:
                continue

            comment = st.text_input(
                "Review comment",
                key=f"workspace_comment_{prompt['id']}",
                placeholder="Optional",
            )
            actions = st.columns(2)
            if actions[0].button("Approve", key=f"workspace_approve_{prompt['id']}", use_container_width=True):
                try:
                    api.approve_prompt(prompt["id"], comment)
                    st.success(f"Prompt #{prompt['id']} moved to production.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed: {e.message}")
            if actions[1].button("Reject", key=f"workspace_reject_{prompt['id']}", use_container_width=True):
                try:
                    api.reject_prompt(prompt["id"], comment)
                    st.warning(f"Prompt #{prompt['id']} returned to draft.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed: {e.message}")


def _activity_feed(activities: list[dict]):
    st.subheader("Recent workspace activity")
    if not activities:
        st.info("No activity recorded yet.")
        return
    for item in activities[:12]:
        st.markdown(f"- {item['event']}  `{item['created_at'][:19]}`")


def render(api: APIClient):
    st.header("Workspace")
    auto_refresh, interval = _refresh_controls("workspace")

    try:
        workspace = api.current_workspace()
        members = api.workspace_members()
        prompts = api.workspace_prompts()
        activities = api.workspace_activity(limit=25)
    except APIError as e:
        st.error(f"Could not load workspace: {e.message}")
        return

    role = _current_workspace_role(members)
    can_review = role in {"admin", "reviewer"}

    cols = st.columns(4)
    cols[0].metric("Workspace", workspace["id"])
    cols[1].metric("Members", len(members))
    cols[2].metric("Shared prompts", len(prompts))
    cols[3].metric("In review", sum(1 for p in prompts if p.get("status") == "review"))
    st.caption(workspace["name"])

    _create_workspace(api)
    _add_member(api, workspace["id"], role)

    st.subheader("Members")
    if members:
        st.dataframe(pd.DataFrame(members), use_container_width=True, hide_index=True)
    else:
        st.info("No members found.")

    st.subheader("Shared prompts")
    if prompts:
        st.dataframe(_prompt_table(prompts), use_container_width=True, hide_index=True)
    else:
        st.info("No shared prompts in this workspace.")

    _approval_queue(api, prompts, can_review)

    st.subheader("Production prompts")
    production = [prompt for prompt in prompts if prompt.get("status") == "production"]
    if production:
        st.dataframe(_prompt_table(production), use_container_width=True, hide_index=True)
    else:
        st.info("No production prompts yet.")

    _activity_feed(activities)

    if auto_refresh:
        time.sleep(interval)
        st.rerun()
