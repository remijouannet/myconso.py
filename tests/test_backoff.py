from __future__ import annotations

import logging
import time

import jwt
import pytest
from aiohttp import ClientSession, web
from aiohttp.client_exceptions import ClientResponseError
from aiohttp.test_utils import AioHTTPTestCase

from myconso.api import MyConsoClient
from myconso.middlewares import exponential_backoff_middleware

logging.basicConfig(level=logging.DEBUG)


class TestMyConsoClientBackoff(AioHTTPTestCase):
    async def get_application(self):
        async def auth(request):
            return web.json_response(
                {
                    "company": "test",
                    "housing": "7552325423",
                    "refresh_token": "FjgyrAD4aw4f3e59snkvsejhn4yywf7w",
                    "token": jwt.encode(
                        {"exp": int(time.time() + 3600), "iat": int(time.time() - 2)},
                        "secret",
                        algorithm="HS256",
                    ),
                    "user": {"email": "test@test.com"},
                }
            )

        async def dashboard(request):
            self.ERROR_429 += 1
            if self.ERROR_429 < 4:
                return web.Response(status=429)

            return web.json_response(
                {
                    "currentMonth": {
                        "endDate": "2025-12-07T12:01:00+00:00",
                        "startDate": "2025-12-01T16:53:16+00:00",
                        "values": [
                            {
                                "counters": ["ED379533C5"],
                                "fluidType": "waterHot",
                                "maxValue": 1.0,
                                "meterType": "waterHot",
                                "minValue": 25.0,
                                "unit": "m3",
                                "value": 1.0,
                                "weightedValue": None,
                            }
                        ],
                    },
                    "lastMonth": {
                        "endDate": "2025-11-30T12:00:00+00:00",
                        "startDate": "2025-11-01T16:53:15+00:00",
                        "values": [
                            {
                                "counters": ["ED379533C5"],
                                "fluidType": "waterHot",
                                "maxValue": 1.0,
                                "meterType": "waterHot",
                                "minValue": 25.0,
                                "unit": "m3",
                                "value": 1.0,
                                "weightedValue": None,
                            }
                        ],
                    },
                }
            )

        self.ERROR_429 = 0
        app = web.Application()
        app.router.add_post("/auth", auth)
        app.router.add_get("/secured/consumption/7552325423/dashboard", dashboard)
        return app

    async def test_backoff(self):
        async with MyConsoClient(username="aaa", password="aaaa") as c:
            # close the existing session before create a new one
            await c.session.close()
            c.session = ClientSession(
                base_url=self.client.make_url(""),
                headers={"user-agent": "aaa"},
                raise_for_status=True,
                middlewares=(
                    exponential_backoff_middleware,
                    c._auth_refresh_middleware,
                ),
            )
            with pytest.raises(ClientResponseError) as exc_info:
                await c.get_dashboard()
            assert exc_info.value.status == 429

            res = await c.get_dashboard()
            assert isinstance(res["currentMonth"], dict)
