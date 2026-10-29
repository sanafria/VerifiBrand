"""HTTP Client for communicating with the BrandLedger FastAPI Backend.

Provides typed, timeout-protected asynchronous calls to the backend endpoints:
- POST /api/scans
- GET /api/scans/{scan_id}
- GET /api/gate/{event_id}
- GET /api/passports/{passport_id}

Handles connection drops, timeouts, 4xx/5xx responses, and sanitized error reporting.
"""
import logging
from typing import Any, Dict, Optional
import httpx

from agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class BackendError(Exception):
    """Base exception for BrandLedger backend communication failures."""
    pass


class BackendConnectionError(BackendError):
    """Raised when the backend server is unreachable or offline."""
    pass


class BackendTimeoutError(BackendError):
    """Raised when a request to the backend times out."""
    pass


class BackendNotFoundError(BackendError):
    """Raised when a requested resource is not found (404)."""
    pass


class BackendResponseError(BackendError):
    """Raised when backend returns an unhandled HTTP error or invalid data."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"Backend HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class BackendClient:
    """Asynchronous HTTP client interface to the BrandLedger backend."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or get_agent_config()
        self.base_url = self.config.BACKEND_URL.rstrip("/")
        self.timeout = self.config.BACKEND_TIMEOUT_SECONDS

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    async def submit_scan(
        self,
        title: str,
        content_text: str,
        draft_id: Optional[str] = None,
        scan_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit creative draft content to POST /api/scans."""
        payload: Dict[str, Any] = {
            "title": title,
            "content_text": content_text,
        }
        if draft_id:
            payload["draft_id"] = draft_id
        if scan_date:
            payload["scan_date"] = scan_date

        url = "/api/scans"
        async with self._client() as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.ConnectError as exc:
                logger.error("Failed to connect to backend at %s: %s", self.base_url, exc)
                raise BackendConnectionError(
                    f"BrandLedger backend unreachable at {self.base_url}. Verify backend service is running."
                ) from exc
            except httpx.TimeoutException as exc:
                logger.error("Timeout connecting to %s%s: %s", self.base_url, url, exc)
                raise BackendTimeoutError(
                    f"Backend request timed out after {self.timeout}s."
                ) from exc
            except Exception as exc:
                logger.error("Unexpected error contacting backend: %s", exc)
                raise BackendError(f"Backend communication error: {str(exc)}") from exc

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except Exception as exc:
                    raise BackendResponseError(
                        response.status_code, "Invalid JSON payload returned by backend."
                    ) from exc

            # Error handling
            detail = self._extract_error_detail(response)
            raise BackendResponseError(response.status_code, detail)

    async def get_scan(self, scan_id: str) -> Dict[str, Any]:
        """Retrieve scan status and findings from GET /api/scans/{scan_id}."""
        url = f"/api/scans/{scan_id.strip()}"
        async with self._client() as client:
            try:
                response = await client.get(url)
            except httpx.ConnectError as exc:
                raise BackendConnectionError(
                    f"BrandLedger backend unreachable at {self.base_url}."
                ) from exc
            except httpx.TimeoutException as exc:
                raise BackendTimeoutError(f"Backend request timed out after {self.timeout}s.") from exc
            except Exception as exc:
                raise BackendError(f"Backend communication error: {str(exc)}") from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    raise BackendResponseError(response.status_code, "Invalid JSON payload.") from exc

            if response.status_code == 404:
                raise BackendNotFoundError(f"Scan attempt '{scan_id}' not found.")

            detail = self._extract_error_detail(response)
            raise BackendResponseError(response.status_code, detail)

    async def get_gate_event(self, event_id: str) -> Dict[str, Any]:
        """Retrieve recorded publication gate decision from GET /api/gate/{event_id}."""
        url = f"/api/gate/{event_id.strip()}"
        async with self._client() as client:
            try:
                response = await client.get(url)
            except httpx.ConnectError as exc:
                raise BackendConnectionError(
                    f"BrandLedger backend unreachable at {self.base_url}."
                ) from exc
            except httpx.TimeoutException as exc:
                raise BackendTimeoutError(f"Backend request timed out after {self.timeout}s.") from exc
            except Exception as exc:
                raise BackendError(f"Backend communication error: {str(exc)}") from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    raise BackendResponseError(response.status_code, "Invalid JSON payload.") from exc

            if response.status_code == 404:
                raise BackendNotFoundError(f"Publication event '{event_id}' not found.")

            detail = self._extract_error_detail(response)
            raise BackendResponseError(response.status_code, detail)

    async def get_passport(self, passport_id: str) -> Dict[str, Any]:
        """Retrieve Content Passport certificate from GET /api/passports/{passport_id}."""
        url = f"/api/passports/{passport_id.strip()}"
        async with self._client() as client:
            try:
                response = await client.get(url)
            except httpx.ConnectError as exc:
                raise BackendConnectionError(
                    f"BrandLedger backend unreachable at {self.base_url}."
                ) from exc
            except httpx.TimeoutException as exc:
                raise BackendTimeoutError(f"Backend request timed out after {self.timeout}s.") from exc
            except Exception as exc:
                raise BackendError(f"Backend communication error: {str(exc)}") from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    raise BackendResponseError(response.status_code, "Invalid JSON payload.") from exc

            if response.status_code == 404:
                raise BackendNotFoundError(f"Content Passport '{passport_id}' not found.")

            detail = self._extract_error_detail(response)
            raise BackendResponseError(response.status_code, detail)

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        """Safely extract error detail string from response body."""
        try:
            body = response.json()
            if isinstance(body, dict) and "detail" in body:
                return str(body["detail"])
            return response.text or f"HTTP {response.status_code}"
        except Exception:
            return response.text or f"HTTP {response.status_code}"
