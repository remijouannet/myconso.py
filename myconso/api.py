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

TOKEN_EXP_DELAY = 10


def check_auth(func):
    async def wrapper(self, *args, **kwargs):
        if not self.token and (self.username and self.password):
            # class has been initialized with username/password
            async with self.lock:
                await self.auth()
        elif not self.housing and self.token and self.refresh_token:
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
    counters: list[dict]
    housings: list[str]
    user: str | None

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
        refresh_middleware: bool = True,
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

        self.housing = None
        self.counters = []
        self.housings = []
        self.user = None

        self.lock = asyncio.Lock()

        middlewares = [exponential_backoff_middleware]
        if refresh_middleware:
            middlewares += [self._auth_refresh_middleware]

        self.session = ClientSession(
            base_url=MYCONSO_API,
            headers={"user-agent": MYCONSO_USER_AGENT},
            raise_for_status=True,
            middlewares=middlewares,
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
        if epoch_now >= self.token_exp - TOKEN_EXP_DELAY:
            log.debug(
                "token is expired, refresh it, exp: %s, time: %s",
                self.token_exp,
                epoch_now,
            )
            async with self.lock:
                res_token = await self.auth_refresh()
                if token := res_token.get("token"):
                    req.headers["authorization"] = f"Bearer {token}"

        res = await handler(req)

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
            self.user = res["user"]["userIdentifier"]
            self.housings = res["user"]["housingIds"]
            self.housing = res["housing"]
            self.token = res["token"]
            self.refresh_token = res["refresh_token"]
            self.token_exp, self.token_iat = decode_jwt(self.token)
            self.session.headers.update({"authorization": f"Bearer {self.token}"})

            log.debug("successful authentification for housing: %s", self.housing)

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
            self.user = res["user"]["userIdentifier"]
            self.housings = res["user"]["housingIds"]
            self.housing = res["housing"]
            self.token = res["token"]
            self.refresh_token = res["refresh_token"]
            self.token_exp, self.token_iat = decode_jwt(self.token)
            self.session.headers.update({"authorization": f"Bearer {self.token}"})

            log.debug(
                "successful authentification for housing (auth_refresh): %s",
                self.housing,
            )

            return res

    @check_auth
    async def get_user(self) -> dict:
        async with self.session.get(f"/secured/users/{self.user}") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_address(self, housing: str | None = None) -> dict:
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/housing/{housing}/address") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_housings(self) -> dict:
        async with self.session.get(f"/secured/users/{self.user}/housings") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_housing(self, housing: str | None = None) -> dict:
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/housing/{housing}") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_dashboard(self, housing: str | None = None) -> dict:
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/consumption/{housing}/dashboard") as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_counters(self) -> list[dict]:
        if not self.counters:
            for housing in self.housings:
                res = await self.get_dashboard(housing)
                for v in res["currentMonth"]["values"]:
                    for counter in v["counters"]:
                        self.counters.append(
                            {
                                "counter": counter,
                                "fluidType": v["fluidType"],
                                "meterType": v["meterType"],
                                "unit": v["unit"],
                                "housing": housing,
                            }
                        )
        return self.counters

    @check_auth
    async def get_consumption(
        self,
        fluidtype: str,
        housing: str | None = None,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> dict | None:
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        housing = housing if housing else self.housing
        async with self.session.get(
            f"/secured/consumption/{housing}/{fluidtype}/day",
            params={
                "startDate": startdate.isoformat(timespec="milliseconds"),
                "endDate": enddate.isoformat(timespec="milliseconds"),
            },
        ) as res:
            return clean_json_ld(await res.json())

    @check_auth
    async def get_meter_info(
        self, counter: str, housing: str | None = None
    ) -> dict | None:
        if not self.counters:
            await self.get_counters()

        housing = housing if housing else self.housing
        for c in self.counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"/secured/meter/{housing}/{c['meterType']}/{c['counter']}/info",
                ) as res:
                    return clean_json_ld(await res.json())
        return None

    @check_auth
    async def get_meter(
        self,
        counter: str,
        housing: str | None = None,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> dict | None:
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        if not self.counters:
            await self.get_counters()

        housing = housing if housing else self.housing
        for c in self.counters:
            if c["counter"] == counter:
                async with self.session.get(
                    f"/secured/meter/{housing}/{c['meterType']}/{c['counter']}",
                    params={
                        "startDate": startdate.isoformat(timespec="milliseconds"),
                        "endDate": enddate.isoformat(timespec="milliseconds"),
                    },
                ) as res:
                    return clean_json_ld(await res.json())
        return None
