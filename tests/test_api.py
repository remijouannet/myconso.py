from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest
from aiohttp.client_exceptions import ClientResponseError

import myconso.api
from myconso.api import MyConsoClient

logging.basicConfig(level=logging.DEBUG)

MYCONSO_HOUSING = os.getenv("MYCONSO_HOUSING")
MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")

class TestMyConsoClientClient:
    @pytest.mark.asyncio
    async def test_get_dashboard(self):
        async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
            await c.auth()
            res = await c.get_dashboard()
            assert isinstance(res["currentMonth"], dict)

    @pytest.mark.asyncio
    async def test_token(self):
        async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
            res = await c.auth()
            assert res["company"] == "proxiserve"
            token = res["token"]
            refresh_token = res["refresh_token"]

        async with MyConsoClient(token=token, refresh_token=refresh_token) as c:
            res = await c.get_housing()
            assert res["housingId"] == MYCONSO_HOUSING

    @pytest.mark.asyncio
    async def test_failed_auth(self):
        async with MyConsoClient(username=MYCONSO_EMAIL, password="aaaaa") as c:
            with pytest.raises(ClientResponseError) as exc_info:
                await c.auth()
            assert exc_info.value.message == "Unauthorized"
            assert exc_info.value.status == 401
