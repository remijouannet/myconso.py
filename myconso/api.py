import asyncio
import logging
import time
from types import TracebackType

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse, ClientSession

from myconso.utils import decode_jwt, first_day_of_the_month, last_day_of_the_month

log = logging.getLogger(__name__)

MYCONSO_API = "https://api.myconso.net"


class MyConso:
    username: str
    password: str
    session: ClientSession
    _counters: list[str]
    _token: str
    _refresh_token: str

    def __init__(
        self,
        username: str,
        password: str,
        session: ClientSession | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.session = session if session else ClientSession()
        self.session.headers.update({"user-agent": "MyConso"})
        self.lock = asyncio.Lock()
        if token and refresh_token:
            self._token = token
            self._token_exp, self._token_iat = decode_jwt(self._token)
            self._refresh_token = refresh_token
        else:
            self._token = None

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    async def login(self):
        async with self.session.post(
            f"{MYCONSO_API}/auth",
            json={
                "email": self.username,
                "password": self.password,
            },
            middlewares=(),
        ) as response:
            token = await response.json()
            self._user = token["user"]["email"]
            self._housing = token["housing"]
            self._token = token["token"]
            self._refresh_token = token["refresh_token"]

            self.token_exp, self.token_iat = decode_jwt(self._token)

            log.debug("successful login for housing: %s", self._housing)

            self.session.headers.update({"authorization": f"Bearer {self._token}"})
            self.session.middlewares = (self._refresh_token_middleware,)

            return token

    def check_login(func):
        async def wrapper(self, *args, **kwargs):
            if not self._token:
                await self.login()
            return await func(self, *args, **kwargs)
        return wrapper

    async def _refresh_token_middleware(
        self, req: ClientRequest, handler: ClientHandlerType
    ) -> ClientResponse:
        epoch_now = time.time()
        if epoch_now > self.token_exp:
            log.debug(
                "token is expired, refresh it exp: %s, time: %s",
                self.token_exp,
                epoch_now,
            )
            async with self.lock:
                await self.refresh_token()

        for _ in range(2):
            resp = await handler(req)
            if resp.status != 401:
                return resp
            else:
                log.debug("received 401, try to refresh the bearer token")
                async with self.lock:
                    await self.refresh_token()

        return resp

    async def refresh_token(self):
        async with self.session.post(
            f"{MYCONSO_API}/auth/refresh",
            json={
                "refresh_token": self._refresh_token,
            },
        ) as response:
            token = await response.json()

            self._user = token["user"]["email"]
            self._housing = token["housing"]
            self._token = token["token"]
            self._refresh_token = token["refresh_token"]

            self.session.headers["authorization"] = f"Bearer {self._token}"

            return token

    async def get_user(self):
        async with self.session.get(
            f"{MYCONSO_API}/secured/users/{self._user}"
        ) as response:
            res = await response.json()
            return res

    async def get_housing(self):
        async with self.session.get(
            f"{MYCONSO_API}/secured/housing/{self._housing}"
        ) as response:
            res = await response.json()
            return res

    @check_login
    async def get_dashboard(self):
        async with self.session.get(
            f"{MYCONSO_API}/secured/consumption/{self._housing}/dashboard"
        ) as response:
            res = await response.json()
            return res

    @check_login
    async def get_counters(self):
        if not self._counters:
            res = await self.get_dashboard()
            for v in res["currentMonth"]["values"]:
                for counter in v["counters"]:
                    self._counters.append(
                        {
                            "counter": counter,
                            "fluidType": v["fluidType"],
                            "meterType": v["meterType"],
                            "unit": v["unit"],
                        }
                    )
        return self._counters

    @check_login
    async def get_consumption(self, fluidtype, startdate=None, enddate=None):
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        async with self.session.get(
            f"{MYCONSO_API}/secured/consumption/{self._housing}/{fluidtype}/day",
            params={"startDate": startdate, "endDate": enddate},
        ) as response:
            res = await response.json()
            return res

    @check_login
    async def get_meter_info(self, counter):
        if not self._counters:
            await self.get_counters()

        for c in self._counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"{MYCONSO_API}/secured/meter/{self._housing}/{c['fluidType']}/{c['counter']}/info",
                ) as response:
                    res = await response.json()
                    return res

    @check_login
    async def get_meter(self, counter, startdate=None, enddate=None):
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        if not self._counters:
            await self.get_counters()

        for c in self._counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"{MYCONSO_API}/secured/meter/{self._housing}/{c['fluidType']}/{c['counter']}",
                    params={"startDate": startdate, "endDate": enddate},
                ) as response:
                    res = await response.json()
                    return res
