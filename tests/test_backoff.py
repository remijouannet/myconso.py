from __future__ import annotations

import logging
import time
import unittest.mock

import pytest
from aiohttp import web
from aiohttp.client_exceptions import ClientResponseError
from aiohttp.test_utils import AioHTTPTestCase

from myconso.api import MyConsoClient
from tests.conftest import create_auth_response, create_dashboard_response

logging.basicConfig(level=logging.DEBUG)


class TestMyConsoClientBackoff(AioHTTPTestCase):
    async def get_application(self):
        async def auth(request):
            return web.json_response(
                create_auth_response(
                    token_exp=int(time.time() + 3600),
                )
            )

        async def dashboard(request):
            self.ERROR_429 += 1
            rate_429 = 4
            if rate_429 > self.ERROR_429:
                return web.Response(status=429)

            return web.json_response(create_dashboard_response())

        self.ERROR_429 = 0
        app = web.Application()
        app.router.add_post("/auth", auth)
        app.router.add_get("/secured/consumption/7552325423/dashboard", dashboard)
        return app

    async def test_backoff(self):
        with unittest.mock.patch(
            "myconso.api.MYCONSO_API", str(self.client.make_url(""))
        ):
            async with MyConsoClient(username="aaa", password="aaaa") as c:
                with pytest.raises(ClientResponseError) as exc_info:
                    await c.get_dashboard()
                assert exc_info.value.status == web.HTTPTooManyRequests.status_code

                res = await c.get_dashboard()
                assert hasattr(res.currentMonth, "startDate")
