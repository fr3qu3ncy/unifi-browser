"""
RemoteUnifiClient — Unifi Cloud API client.

Two-phase API:
  1. Cloud API  (https://api.ui.com/v1/) for /sites and /hosts/{hostId}
  2. Network API via connector proxy for devices/clients/networks/wifi
"""
from __future__ import annotations

import asyncio
import json as _json
from pathlib import Path

import httpx

REMOTE_DEFAULT_API_URL = "https://api.ui.com/v1/"
_NETWORK_PROXY = "/proxy/network/integration/v1"


class RemoteUrlHistory:
    """Persists recent remote API keys / URLs."""

    _PATH: Path = Path.home() / ".config" / "unifi-browser" / "remote_history.json"
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
        self._urls = [url] + [u for u in self._urls if u != url]
        self._urls = self._urls[: self._MAX]
        self.save()

    @property
    def urls(self) -> list[str]:
        return list(self._urls)

    @property
    def last(self) -> str:
        return self._urls[0] if self._urls else REMOTE_DEFAULT_API_URL


remote_url_history = RemoteUrlHistory()


class RemoteUnifiClient:
    """Async Unifi Cloud REST API client."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http = httpx.AsyncClient(verify=True, timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def _cloud_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _network_url(self, host_id: str, path: str) -> str:
        return f"{self.base_url}/connector/consoles/{host_id}{_NETWORK_PROXY}{path}"

    async def _fetch_all_cloud(self, path: str) -> list[dict]:
        """Fetch all pages from a paginated cloud endpoint."""
        results: list[dict] = []
        next_token: str | None = None
        while True:
            params: dict = {"pageSize": 100}
            if next_token:
                params["nextToken"] = next_token
            resp = await self._http.get(
                self._cloud_url(path), params=params, headers=self._headers()
            )
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data", [])
            results.extend(data)
            next_token = body.get("nextToken")
            if not next_token or not data:
                break
        return results

    async def _fetch_all_network(self, host_id: str, path: str) -> list[dict]:
        """Fetch all pages from a paginated network API endpoint via connector."""
        results: list[dict] = []
        offset = 0
        limit = 100
        while True:
            resp = await self._http.get(
                self._network_url(host_id, path),
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

    # ── Cloud API ─────────────────────────────────────────────────────────────

    async def get_sites(self) -> list[dict]:
        """Fetch all sites from the cloud API, enriched with host info."""
        sites = await self._fetch_all_cloud("/sites")
        # Enrich with host data in parallel (best-effort; skip on error)
        host_ids = list({s.get("hostId") for s in sites if s.get("hostId")})
        host_map: dict[str, dict] = {}
        if host_ids:
            results = await asyncio.gather(
                *[self._get_host_safe(hid) for hid in host_ids]
            )
            for hid, info in zip(host_ids, results):
                if info:
                    host_map[hid] = info
        for site in sites:
            hid = site.get("hostId", "")
            if hid in host_map:
                site["_hostInfo"] = host_map[hid]
        return sites

    async def _get_host_safe(self, host_id: str) -> dict | None:
        try:
            return await self.get_host(host_id)
        except Exception as exc:
            # Store the error so the app can surface it if needed
            self._last_host_error = str(exc)
            return None

    async def get_host(self, host_id: str) -> dict:
        resp = await self._http.get(
            self._cloud_url(f"/hosts/{host_id}"), headers=self._headers()
        )
        resp.raise_for_status()
        body = resp.json()
        # Cloud API may return {"data": {...}} or {"data": [{...}]}
        data = body.get("data", {})
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    async def get_hosts(self) -> list[dict]:
        """Fetch all hosts from the cloud API."""
        return await self._fetch_all_cloud("/hosts")

    # ── Network API (via connector) ───────────────────────────────────────────

    async def get_network_sites(self, host_id: str) -> list[dict]:
        """Get network-API site list for a given host."""
        resp = await self._http.get(
            self._network_url(host_id, "/sites"), headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_devices(self, host_id: str, site_id: str) -> list[dict]:
        return await self._fetch_all_network(host_id, f"/sites/{site_id}/devices")

    async def get_clients(self, host_id: str, site_id: str) -> list[dict]:
        return await self._fetch_all_network(host_id, f"/sites/{site_id}/clients")

    async def get_networks(self, host_id: str, site_id: str) -> list[dict]:
        return await self._fetch_all_network(host_id, f"/sites/{site_id}/networks")

    async def get_network(self, host_id: str, site_id: str, network_id: str) -> dict:
        resp = await self._http.get(
            self._network_url(host_id, f"/sites/{site_id}/networks/{network_id}"),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_wifi_broadcasts(self, host_id: str, site_id: str) -> list[dict]:
        return await self._fetch_all_network(host_id, f"/sites/{site_id}/wifi/broadcasts")

    async def get_wifi_broadcast(self, host_id: str, site_id: str, broadcast_id: str) -> dict:
        resp = await self._http.get(
            self._network_url(host_id, f"/sites/{site_id}/wifi/broadcasts/{broadcast_id}"),
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_isp_metrics(self, type_: str = "5m", duration: str = "24h") -> list[dict]:
        """Fetch ISP metrics for all hosts on the account."""
        resp = await self._http.get(
            self._cloud_url(f"/isp-metrics/{type_}"),
            params={"duration": duration},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_wans(self, host_id: str, site_id: str) -> list[dict]:
        return await self._fetch_all_network(host_id, f"/sites/{site_id}/wans")

    async def close(self) -> None:
        await self._http.aclose()
