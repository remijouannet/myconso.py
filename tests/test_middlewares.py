from __future__ import annotations

from typing import ClassVar
from unittest.mock import patch

import pytest
from aiohttp import ClientSession, web
from aiohttp.client_exceptions import ClientResponseError
from aiohttp.test_utils import AioHTTPTestCase

from myconso import middlewares

# HTTP status code constants for readability
HTTP_OK = 200
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVICE_UNAVAILABLE = 503
EXPECTED_CALL_COUNT = 2


class BaseBackoffTest(AioHTTPTestCase):
    """Base class providing common utilities for backoff tests."""

    # Override in subclasses with the sequence of status codes to return
    status_sequence: ClassVar[list[int]] = []

    async def get_application(self):
        self.call_index = 0

        async def handler(request):
            idx = self.call_index
            self.call_index += 1
            # Choose status based on the predefined sequence
            if idx < len(self.status_sequence):
                status = self.status_sequence[idx]
            else:
                status = self.status_sequence[-1]
            if status == HTTP_OK:
                return web.json_response({"ok": True})
            return web.Response(status=status)

        app = web.Application()
        app.router.add_get("/test", handler)
        return app

    async def _client_session(self):
        """Create a ClientSession that uses only the exponential backoff middleware."""
        return ClientSession(
            base_url=self.client.make_url(""),
            raise_for_status=True,
            middlewares=(middlewares.exponential_backoff_middleware,),
        )


class TestExponentialBackoffNoRetry(BaseBackoffTest):
    status_sequence: ClassVar[list[int]] = [HTTP_OK]

    @pytest.mark.asyncio
    async def test_no_retry(self):
        async def _sleep(delay: float):
            return

        # Patch asyncio.sleep to avoid real delays

        with patch("asyncio.sleep", new=_sleep):
            async with await self._client_session() as session:
                async with session.get("/test") as resp:
                    data = await resp.json()
                    assert data["ok"] is True


class TestExponentialBackoffRetrySuccess(BaseBackoffTest):
    status_sequence: ClassVar[list[int]] = [HTTP_TOO_MANY_REQUESTS, HTTP_OK]

    @pytest.mark.asyncio
    async def test_retry_success(self):
        async def _sleep(delay: float):
            return

        with patch("asyncio.sleep", new=_sleep):
            async with await self._client_session() as session:
                async with session.get("/test") as resp:
                    data = await resp.json()
                    assert data["ok"] is True
                    # Ensure the handler was called twice (initial + one retry)

                    assert self.call_index == EXPECTED_CALL_COUNT


class TestExponentialBackoffRetryExhausted(BaseBackoffTest):
    # Three attempts (initial + 2 retries) all return a backoff status
    status_sequence: ClassVar[list[int]] = [
        HTTP_SERVICE_UNAVAILABLE,
        HTTP_SERVICE_UNAVAILABLE,
        HTTP_SERVICE_UNAVAILABLE,
    ]

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        async def _sleep(delay: float):
            return

        with patch("asyncio.sleep", new=_sleep):
            async with await self._client_session() as session:
                with pytest.raises(ClientResponseError) as exc_info:
                    await session.get("/test")
                assert exc_info.value.status == HTTP_SERVICE_UNAVAILABLE
                # Handler should have been called three times (initial + two retries)
