from __future__ import annotations

import logging
import os
from aiohttp.client_exceptions import ClientResponseError
import pytest

from myconso.api import MyConso

logging.basicConfig(level=logging.DEBUG)

MYCONSO_HOUSING = os.getenv("MYCONSO_HOUSING")
MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")

FAKE_BEARER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30"

class TestMyConsoClient:
    @pytest.mark.asyncio
    async def test_get_dashboard(self):
        async with MyConso(
            username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD
        ) as c:
            await c.auth()
            res = await c.get_dashboard()
            assert isinstance(res['currentMonth'], dict)

    @pytest.mark.asyncio
    async def test_token(self):
        async with MyConso(
            username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD
        ) as c:
            res = await c.auth()
            assert res['company'] == "proxiserve"
            token = res['token']
            refresh_token = res['refresh_token']

        async with MyConso(
            token=token, refresh_token=refresh_token
        ) as c:
            res = await c.get_housing()
            assert res['housingId'] == MYCONSO_HOUSING

    @pytest.mark.asyncio
    async def test_refresh_token_1(self):
        async with MyConso(
            username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD
        ) as c:
            res = await c.get_dashboard()
            assert isinstance(res['currentMonth'], dict)

            res = await c.auth_refresh()
            c.session.headers.update({"authorization": f"Bearer {FAKE_BEARER}"})
            with pytest.raises(ClientResponseError) as exc_info:
                res = await c.get_dashboard()
            assert exc_info.value.message == "Unauthorized"
            assert exc_info.value.status == 401
            assert str(exc_info.value.request_info.real_url) == "https://api.myconso.net/auth/refresh"

    @pytest.mark.asyncio
    async def test_failed_auth(self):
        async with MyConso(
            username=MYCONSO_EMAIL, password="aaaaa"
        ) as c:
            with pytest.raises(ClientResponseError) as exc_info:
                res = await c.auth()
            assert exc_info.value.message == "Unauthorized"
            assert exc_info.value.status == 401
