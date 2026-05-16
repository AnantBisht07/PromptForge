import os
import time
from typing import Any, Optional

import requests


class APIError(Exception):
    """Raised when the backend returns a non-2xx response."""

    def __init__(self, status: int, message: str):
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message


class AuthExpired(APIError):
    """401 - token missing, invalid, or expired. UI should prompt re-login."""


class PermissionDenied(APIError):
    """403 - authenticated but role lacks access to this endpoint."""


def _extract_detail(resp: requests.Response) -> str:
    try:
        body = resp.json()
        return body.get("detail") or str(body)
    except ValueError:
        return resp.text or resp.reason


class APIClient:
    """Thin typed wrapper around requests for the PromptForge FastAPI backend."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or os.getenv("PROMPTFORGE_API_URL", "http://localhost:8000")).rstrip("/")
        self.token: Optional[str] = token

    def _headers(self, auth: bool = True) -> dict:
        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, *, auth: bool = True, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(method, url, headers=self._headers(auth=auth), timeout=60, **kwargs)
        except requests.RequestException as e:
            raise APIError(0, f"Network error contacting {url}: {e}")

        if resp.status_code == 401:
            raise AuthExpired(401, _extract_detail(resp))
        if resp.status_code == 403:
            raise PermissionDenied(403, _extract_detail(resp))
        if not resp.ok:
            raise APIError(resp.status_code, _extract_detail(resp))

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # --- Auth ---

    def register(self, username: str, password: str, role: str = "developer") -> dict:
        return self._request(
            "POST",
            "/auth/register",
            auth=False,
            json={"username": username, "password": password, "role": role},
        )

    def login(self, username: str, password: str) -> str:
        body = self._request(
            "POST",
            "/auth/login",
            auth=False,
            json={"username": username, "password": password},
        )
        self.token = body["access_token"]
        return self.token

    def me(self) -> dict:
        return self._request("GET", "/users/me")

    # --- Workspace ---

    def current_workspace(self) -> dict:
        return self._request("GET", "/workspace/current")

    def create_workspace(self, name: str) -> dict:
        return self._request("POST", "/workspace/create", json={"name": name})

    def add_member(
        self,
        role: str,
        workspace_id: int | None = None,
        username: str | None = None,
        user_id: int | None = None,
    ) -> dict:
        payload = {"role": role, "workspace_id": workspace_id}
        if username:
            payload["username"] = username
        if user_id is not None:
            payload["user_id"] = user_id
        return self._request("POST", "/workspace/add-member", json=payload)

    def workspace_members(self) -> list[dict]:
        return self._request("GET", "/workspace/members")

    def workspace_prompts(self) -> list[dict]:
        return self._request("GET", "/workspace/prompts")

    def workspace_activity(self, limit: int = 25) -> list[dict]:
        return self._request("GET", f"/workspace/activity?limit={limit}")

    def workspace_analytics(self) -> dict:
        return self._request("GET", "/workspace/analytics")

    # --- Prompts ---

    def list_prompts(self) -> list[dict]:
        return self._request("GET", "/prompts/list")

    def create_prompt(self, content: str, status: str = "review") -> dict:
        return self._request("POST", "/prompts/create", json={"content": content, "status": status})

    def update_prompt(self, prompt_id: int, content: str, status: str = "review") -> dict:
        return self._request(
            "PUT",
            f"/prompts/{prompt_id}",
            json={"content": content, "status": status},
        )

    def get_versions(self, prompt_id: int) -> list[dict]:
        return self._request("GET", f"/prompts/{prompt_id}/versions")

    def approve_prompt(self, prompt_id: int, comment: str = "") -> dict:
        return self._request(
            "POST",
            "/prompts/approve",
            json={"prompt_id": prompt_id, "comment": comment},
        )

    def reject_prompt(self, prompt_id: int, comment: str = "") -> dict:
        return self._request(
            "POST",
            "/prompts/reject",
            json={"prompt_id": prompt_id, "comment": comment},
        )

    def search(self, query: str) -> list[dict]:
        results = self._request("POST", "/prompts/search", json={"query": query})
        if results:
            try:
                lookup = {str(p["id"]): p["content"] for p in self.list_prompts()}
                for result in results:
                    if not result.get("content"):
                        result["content"] = lookup.get(str(result["prompt_id"]), "")
            except APIError:
                pass
        return results

    # --- Evaluation and experiments ---

    def evaluate(self, prompt: str, prompt_id: int | None = None) -> dict:
        payload = {"prompt": prompt}
        if prompt_id is not None:
            payload["prompt_id"] = prompt_id

        started = time.perf_counter()
        body = self._request("POST", "/evaluate", json=payload)
        body.setdefault("latency_ms", round((time.perf_counter() - started) * 1000.0, 1))
        return body

    def run_ab_test(
        self,
        prompt_id: int,
        version_a: int,
        version_b: int,
        test_input: str,
        rounds: int = 5,
    ) -> dict:
        return self._request(
            "POST",
            "/ab-test",
            json={
                "prompt_id": prompt_id,
                "version_a": version_a,
                "version_b": version_b,
                "test_input": test_input,
                "rounds": rounds,
            },
        )

    # --- Analytics and feedback ---

    def analytics(self) -> dict:
        return self._request("GET", "/analytics")

    def add_feedback(self, prompt_id: int, decision: str = "comment", comment: str = "") -> dict:
        return self._request(
            "POST",
            "/feedback",
            json={"prompt_id": prompt_id, "decision": decision, "comment": comment},
        )

    def list_feedback(self) -> list[dict]:
        return self._request("GET", "/feedback")
