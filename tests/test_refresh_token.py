from __future__ import annotations

import asyncio
import logging
import time

import jwt
from aiohttp import ClientSession, web
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
                        {"exp": int(time.time() + 2), "iat": int(time.time())},
                        "secret",
                        algorithm="HS256",
                    ),
                    "user": {
                        "email": "test@test.com",
                        "userIdentifier": "test@test.com",
                        "housingIds": ["7552325423"],
                    },
                }
            )

        async def auth_refresh(request):
            return web.json_response(
                {
                    "company": "test",
                    "housing": "7552325423",
                    "refresh_token": "szxFemwbwfowduccEvD7imzcjtn5kEo7",
                    "token": jwt.encode(
                        {"exp": int(time.time() + 2), "iat": int(time.time())},
                        "secret",
                        algorithm="HS256",
                    ),
                    "user": {
                        "email": "test@test.com",
                        "userIdentifier": "test@test.com",
                        "housingIds": ["7552325423"],
                    },
                }
            )

        async def dashboard(request):
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

        async def housing(request):
            return web.json_response(
                {
                    "housingId": "7552325423",
                    "name": "Logement 10",
                    "entryDate": "2024-05-30T00:00:00+00:00",
                    "surface": 40,
                    "numberInhabitants": 2,
                    "housingType": "t2",
                    "energyLabel": "A",
                    "company": "proxiserve",
                    "proofStatus": "validated",
                    "isActive": True,
                    "proofUploadDate": "2025-04-05T20:26:24+00:00",
                    "createdAt": "2025-04-02T10:10:58+00:00",
                }
            )

        self.ERROR_401 = 0

        app = web.Application()
        app.router.add_post("/auth", auth)
        app.router.add_post("/auth/refresh", auth_refresh)
        app.router.add_get("/secured/consumption/7552325423/dashboard", dashboard)
        app.router.add_get("/secured/housing/7552325423", housing)
        return app

    async def test_refresh_token_1(self):
        async with MyConsoClient(username="aaa", password="aaaa") as c:
            # close the existing session before creating a new one
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
            res = await c.get_dashboard()
            assert isinstance(res["currentMonth"], dict)

    async def test_refresh_token_2(self):
        async with MyConsoClient(username="aaa", password="aaaa") as c:
            # close the existing session before creating a new one
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
            res = await c.get_dashboard()
            assert isinstance(res["currentMonth"], dict)

            await asyncio.sleep(4)

            res = await c.get_dashboard()
            assert isinstance(res["currentMonth"], dict)

    async def test_refresh_token_4(self):
        async with MyConsoClient(username="aaa", password="aaaa") as c:
            # close the existing session before creating a new one
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
            res = await c.get_housing()
            assert res["housingId"] == "7552325423"

            token1 = c.token

            await asyncio.sleep(4)

            assert token1 == c.token
            res = await c.get_housing()
            assert token1 != c.token
            assert res["housingId"] == "7552325423"
