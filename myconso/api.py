import asyncio
import logging
import time
from datetime import datetime
from types import TracebackType

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse, ClientSession

from myconso.middlewares import exponential_backoff_middleware
from myconso.utils import (
    clean_json_ld,
    decode_jwt,
    first_day_of_the_month,
    last_day_of_the_month,
)

log = logging.getLogger(__name__)

MYCONSO_API = "https://api.myconso.net"
MYCONSO_USER_AGENT = "MyConso"


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


class MyConsoClient:
    username: str | None
    password: str | None
    token: str | None
    refresh_token: str | None
    _counters: list[dict]

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
        elif username and password:
            self.token = None
            self.refresh_token = None
            self.username = username
            self.password = password
        else:
            raise ValueError(
                "You must either provide username/password or token/refresh_token"
            )

        self._housing = None
        self._counters = []
        self.lock = asyncio.Lock()
        self.session = ClientSession(
            base_url=MYCONSO_API,
            headers={"user-agent": MYCONSO_USER_AGENT},
            raise_for_status=True,
            middlewares=(
                exponential_backoff_middleware,
                self._auth_refresh_middleware,
            ),
        )

    async def __aenter__(self) -> "MyConsoClient":
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
            res = await handler(req)
            if res.status in {401}:
                log.debug("received %s, try to refresh the bearer token", res.status)
                async with self.lock:
                    await self.auth_refresh()
            else:
                return res

        return res

    async def auth(self) -> dict:
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

    async def auth_refresh(self) -> dict:
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
    async def get_user(self) -> dict:
        async with self.session.get(f"/secured/users/{self._user}") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_housing(self) -> dict:
        async with self.session.get(f"/secured/housing/{self._housing}") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_dashboard(self) -> dict:
        async with self.session.get(
            f"/secured/consumption/{self._housing}/dashboard"
        ) as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_counters(self) -> list[dict]:
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
    async def get_consumption(
        self,
        fluidtype: str,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> dict | None:
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
        ) as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_meter_info(self, counter: str) -> dict | None:
        if not self._counters:
            await self.get_counters()

        for c in self._counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"/secured/meter/{self._housing}/{c['meterType']}/{c['counter']}/info",
                ) as res:
                    return clean_json_ld(await res.json())
        return None

    @check_auth
    async def get_meter(
        self,
        counter: str,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> dict | None:
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        if not self._counters:
            await self.get_counters()

        for c in self._counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"/secured/meter/{self._housing}/{c['meterType']}/{c['counter']}",
                    params={
                        "startDate": startdate.isoformat(timespec="milliseconds"),
                        "endDate": enddate.isoformat(timespec="milliseconds"),
                    },
                ) as res:
                    return clean_json_ld(await res.json())
        return None
