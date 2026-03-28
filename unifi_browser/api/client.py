"""
Unifi local REST API client and URL history persistence.
"""
from __future__ import annotations

import json as _json
from pathlib import Path

import httpx

from unifi_browser.constants import DEFAULT_API_URL


class UrlHistory:
    """Persists a list of recently used controller URLs to disk."""

    _PATH: Path = Path.home() / ".config" / "unifi-browser" / "history.json"
    _MAX: int = 10

    def __init__(self) -> None:
        self._urls: list[str] = self._load()

    def _load(self) -> list[str]:
        try:
            data = _json.loads(self._PATH.read_text())
            return [u for u in data if isinstance(u, str)][: self._MAX]
        except Exception:
            return []

    def save(self) -> None:
        self._PATH.parent.mkdir(parents=True, exist_ok=True)
        self._PATH.write_text(_json.dumps(self._urls))

    def add(self, url: str) -> None:
        """Add url to the front; deduplicate; trim to _MAX entries."""
        self._urls = [url] + [u for u in self._urls if u != url]
        self._urls = self._urls[: self._MAX]
        self.save()

    @property
    def urls(self) -> list[str]:
        return list(self._urls)

    @property
    def last(self) -> str:
        return self._urls[0] if self._urls else DEFAULT_API_URL


# Module-level singleton — created once at import time.
url_history = UrlHistory()


class UnifiClient:
    """Async Unifi local REST API client (SSL verification disabled for self-signed certs)."""

    _API_BASE = "/proxy/network/integration/v1"

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http = httpx.AsyncClient(verify=False, timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self._API_BASE}{path}"

    async def _fetch_all(self, path: str) -> list[dict]:
        """Fetch all pages from a paginated endpoint."""
        results: list[dict] = []
        offset = 0
        limit = 100
        while True:
            resp = await self._http.get(
                self._url(path),
                params={"limit": limit, "offset": offset},
                headers=self._headers(),
            )
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data", [])
            results.extend(data)
            if offset + len(data) >= body.get("totalCount", 0) or not data:
                break
            offset += len(data)
        return results

    async def get_sites(self) -> list[dict]:
        resp = await self._http.get(self._url("/sites"), headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_devices(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/devices")

    async def get_clients(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/clients")

    async def get_networks(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/networks")

    async def get_network(self, site_id: str, network_id: str) -> dict:
        resp = await self._http.get(
            self._url(f"/sites/{site_id}/networks/{network_id}"),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_wifi_broadcasts(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/wifi/broadcasts")

    async def get_wifi_broadcast(self, site_id: str, broadcast_id: str) -> dict:
        resp = await self._http.get(
            self._url(f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}"),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_wans(self, site_id: str) -> list[dict]:
        return await self._fetch_all(f"/sites/{site_id}/wans")

    async def close(self) -> None:
        await self._http.aclose()
