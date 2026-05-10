import pandas as pd
import streamlit as st

from frontend.api.client import APIClient, APIError


def _prompt_rows(prompts: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": prompt["id"],
            "status": prompt.get("status", "review"),
            "versions": len(prompt.get("versions", [])),
            "created_at": prompt["created_at"][:19],
            "content": prompt["content"][:140],
        }
        for prompt in prompts
    ])


def render(api: APIClient):
    st.header("Reviewer queue")

    if st.button("Refresh", key="reviewer_refresh", use_container_width=False):
        st.rerun()

    try:
        prompts = api.workspace_prompts()
    except APIError as e:
        st.error(f"Could not load prompts: {e.message}")
        return

    review_prompts = [prompt for prompt in prompts if prompt.get("status") == "review"]
    production_prompts = [prompt for prompt in prompts if prompt.get("status") == "production"]
    draft_prompts = [prompt for prompt in prompts if prompt.get("status") == "draft"]

    cols = st.columns(4)
    cols[0].metric("All prompts", len(prompts))
    cols[1].metric("In review", len(review_prompts))
    cols[2].metric("Production", len(production_prompts))
    cols[3].metric("Draft", len(draft_prompts))

    if not review_prompts:
        st.info("No prompts are waiting for approval.")
    else:
        for prompt in review_prompts:
            with st.container(border=True):
                st.markdown(f"**Prompt #{prompt['id']}**")
                st.code(prompt["content"], language="markdown")
                versions = prompt.get("versions", [])
                if versions:
                    st.caption(f"{len(versions)} version(s), latest v{versions[-1]['version_number']}")

                comment = st.text_area(
                    "Review comment",
                    key=f"reviewer_comment_{prompt['id']}",
                    height=80,
                )
                actions = st.columns(2)
                if actions[0].button("Approve", key=f"reviewer_approve_{prompt['id']}", use_container_width=True):
                    try:
                        api.approve_prompt(prompt["id"], comment)
                        st.success(f"Prompt #{prompt['id']} moved to production.")
                        st.rerun()
                    except APIError as e:
                        st.error(f"Failed: {e.message}")

                if actions[1].button("Reject", key=f"reviewer_reject_{prompt['id']}", use_container_width=True):
                    try:
                        api.reject_prompt(prompt["id"], comment)
                        st.warning(f"Prompt #{prompt['id']} returned to draft.")
                        st.rerun()
                    except APIError as e:
                        st.error(f"Failed: {e.message}")

    if production_prompts:
        st.subheader("Production prompts")
        st.dataframe(_prompt_rows(production_prompts), use_container_width=True, hide_index=True)

    if draft_prompts:
        st.subheader("Rejected drafts")
        st.dataframe(_prompt_rows(draft_prompts), use_container_width=True, hide_index=True)
