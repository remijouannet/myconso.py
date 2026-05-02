from __future__ import annotations

import asyncio
import time
import unittest.mock

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from myconso.api import MyConsoClient
from tests.conftest import (
    create_auth_response,
    create_dashboard_response,
    create_housing_response,
)


class TestMyConsoClientBackoff(AioHTTPTestCase):
    async def get_application(self):
        async def auth(request):
            return web.json_response(
                create_auth_response(
                    token_exp=int(time.time() + 2),
                )
            )

        async def auth_refresh(request):
            return web.json_response(
                create_auth_response(
                    token_exp=int(time.time() + 2),
                    refresh_token="szxFemwbwfowduccEvD7imzcjtn5kEo7",
                )
            )

        async def dashboard(request):
            return web.json_response(create_dashboard_response())

        async def housing(request):
            return web.json_response(create_housing_response())

        self.ERROR_401 = 0

        app = web.Application()
        app.router.add_post("/auth", auth)
        app.router.add_post("/auth/refresh", auth_refresh)
        app.router.add_get("/secured/consumption/7552325423/dashboard", dashboard)
        app.router.add_get("/secured/housing/7552325423", housing)
        return app

    async def test_refresh_token_1(self):
        with unittest.mock.patch(
            "myconso.api.MYCONSO_API", str(self.client.make_url(""))
        ):
            async with MyConsoClient(username="aaa", password="aaaa") as c:
                res = await c.get_dashboard()
                assert hasattr(res.currentMonth, "startDate")

    async def test_refresh_token_2(self):
        with unittest.mock.patch(
            "myconso.api.MYCONSO_API", str(self.client.make_url(""))
        ):
            async with MyConsoClient(username="aaa", password="aaaa") as c:
                res = await c.get_dashboard()
                assert hasattr(res.currentMonth, "startDate")

                await asyncio.sleep(4)

                res = await c.get_dashboard()
                assert hasattr(res.currentMonth, "startDate")

                await asyncio.sleep(4)

                res = await c.get_dashboard()
                assert hasattr(res.currentMonth, "startDate")

    async def test_refresh_token_4(self):
        with unittest.mock.patch(
            "myconso.api.MYCONSO_API", str(self.client.make_url(""))
        ):
            async with MyConsoClient(username="aaa", password="aaaa") as c:
                res = await c.get_housing()
                assert res.housingId == "7552325423"

                token1 = c.token

                await asyncio.sleep(4)

                assert token1 == c.token
                res = await c.get_housing()
                assert token1 != c.token
                assert res.housingId == "7552325423"
