import asyncio
import logging
import time
from types import TracebackType

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse, ClientSession
from aiohttp.client_exceptions import ClientResponseError

from myconso.middlewares import exponential_backoff_middleware
from myconso.utils import (
    clean_hydra,
    decode_jwt,
    first_day_of_the_month,
    last_day_of_the_month,
)

log = logging.getLogger(__name__)

MYCONSO_API = "https://api.myconso.net"
MYCONSO_USER_AGENT = "MyConso"

class MyConso:
    username: str
    password: str
    session: ClientSession
    token: str
    refresh_token: str
    _counters: list[str]

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        if token and refresh_token:
            self.token = token
            self.token_exp, self.token_iat = decode_jwt(self.token)
            self.refresh_token = refresh_token
        else:
            self.token = None
            self.refresh_token = None
            self.username = username
            self.password = password

        self._housing = None
        self._counters = []
        self.lock = asyncio.Lock()
        self.session = ClientSession(
            base_url=MYCONSO_API,
            headers={"user-agent": MYCONSO_USER_AGENT},
            raise_for_status=True,
            middlewares = (
                exponential_backoff_middleware,
                self._auth_refresh_middleware,
            ),
        )

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

    async def _auth_refresh_middleware(
        self, req: ClientRequest, handler: ClientHandlerType
    ) -> ClientResponse:
        log.debug("middleware _auth_refresh_middleware %s", req.url)

        epoch_now = time.time()
        if epoch_now > self.token_exp:
            log.debug(
                "token is expired, refresh it, exp: %s, time: %s",
                self.token_exp,
                epoch_now,
            )
            async with self.lock:
                await self.auth_refresh()

        for _ in range(2):
            resp = await handler(req)
            if resp.status in {401, 403}:
                log.debug("received %s, try to refresh the bearer token", resp.status)
                async with self.lock:
                    await self.auth_refresh()
            else:
                return resp

        return resp

    def check_auth(func):
        async def wrapper(self, *args, **kwargs):
            if not self.token and (self.username and self.password):
                # class has been initialized with username/password
                async with self.lock:
                    await self.auth()
            elif not self._housing and self.token and self.refresh_token:
                # class has been initialized with token/refresh_token
                async with self.lock:
                    await self.auth_refresh()
            return await func(self, *args, **kwargs)

        return wrapper

    async def auth(self):
        async with self.session.post(
            "/auth",
            json={
                "email": self.username,
                "password": self.password,
            },
            middlewares=(),
        ) as response:
            res = await response.json()
            self._user = res["user"]["email"]
            self._housing = res["housing"]
            self.token = res["token"]
            self.refresh_token = res["refresh_token"]
            self.token_exp, self.token_iat = decode_jwt(self.token)
            self.session.headers.update({"authorization": f"Bearer {self.token}"})

            log.debug("successful authentification for housing: %s", self._housing)

            return res

    async def auth_refresh(self):
        async with self.session.post(
            "/auth/refresh",
            json={
                "refresh_token": self.refresh_token,
            },
            middlewares=(),
        ) as response:
            res = await response.json()
            self._user = res["user"]["email"]
            self._housing = res["housing"]
            self.token = res["token"]
            self.refresh_token = res["refresh_token"]
            self.token_exp, self.token_iat = decode_jwt(self.token)
            self.session.headers["authorization"] = f"Bearer {self.token}"

            return res

    @check_auth
    async def get_user(self):
        async with self.session.get(f"/secured/users/{self._user}") as response:
            return clean_hydra(await response.json())

    @check_auth
    async def get_housing(self):
        async with self.session.get(f"/secured/housing/{self._housing}") as response:
            return clean_hydra(await response.json())

    @check_auth
    async def get_dashboard(self):
        async with self.session.get(
            f"/secured/consumption/{self._housing}/dashboard"
        ) as response:
            return clean_hydra(await response.json())

    @check_auth
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

    @check_auth
    async def get_consumption(self, fluidtype, startdate=None, enddate=None):
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        async with self.session.get(
            f"/secured/consumption/{self._housing}/{fluidtype}/day",
            params={
                "startDate": startdate.isoformat(timespec="milliseconds"),
                "endDate": enddate.isoformat(timespec="milliseconds"),
            },
        ) as response:
            return clean_hydra(await response.json())

    @check_auth
    async def get_meter_info(self, counter):
        if not self._counters:
            await self.get_counters()

        for c in self._counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"/secured/meter/{self._housing}/{c['fluidType']}/{c['counter']}/info",
                ) as response:
                    return clean_hydra(await response.json())

    @check_auth
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
                    f"/secured/meter/{self._housing}/{c['fluidType']}/{c['counter']}",
                    params={
                        "startDate": startdate.isoformat(timespec="milliseconds"),
                        "endDate": enddate.isoformat(timespec="milliseconds"),
                    },
                ) as response:
                    return clean_hydra(await response.json())
