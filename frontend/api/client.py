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
    """401 — token missing, invalid, or expired. UI should prompt re-login."""


class PermissionDenied(APIError):
    """403 — authenticated but role lacks access to this endpoint."""


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
            resp = requests.request(method, url, headers=self._headers(auth=auth), timeout=30, **kwargs)
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
            "POST", "/auth/register",
            auth=False,
            json={"username": username, "password": password, "role": role},
        )

    def login(self, username: str, password: str) -> str:
        body = self._request(
            "POST", "/auth/login",
            auth=False,
            json={"username": username, "password": password},
        )
        self.token = body["access_token"]
        return self.token

    def me(self) -> dict:
        return self._request("GET", "/users/me")

    # --- Prompts ---

    def list_prompts(self) -> list[dict]:
        return self._request("GET", "/prompts/list")

    def create_prompt(self, content: str) -> dict:
        return self._request("POST", "/prompts/create", json={"content": content})

    def get_versions(self, prompt_id: int) -> list[dict]:
        return self._request("GET", f"/prompts/{prompt_id}/versions")

    def search(self, query: str) -> list[dict]:
        results = self._request("POST", "/prompts/search", json={"query": query})
        # Backend returns content="" — enrich from /prompts/list (one extra call)
        if results:
            try:
                lookup = {str(p["id"]): p["content"] for p in self.list_prompts()}
                for r in results:
                    if not r.get("content"):
                        r["content"] = lookup.get(str(r["prompt_id"]), "")
            except APIError:
                pass
        return results

    # --- Evaluation ---

    def evaluate(self, prompt: str) -> dict:
        """POST /evaluate, returns {prompt, output, score, latency_ms}.

        latency_ms is measured client-side around the HTTP call since the
        backend doesn't include timing in its response.
        """
        t0 = time.perf_counter()
        body = self._request("POST", "/evaluate", json={"prompt": prompt})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        body["latency_ms"] = round(elapsed_ms, 1)
        return body
