import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from types import TracebackType
from typing import Concatenate, ParamSpec, TypeVar

from aiohttp import (
    ClientHandlerType,
    ClientRequest,
    ClientResponse,
    ClientSession,
    DummyCookieJar,
)

from myconso.middlewares import exponential_backoff_middleware

# Typed models for API responses
from myconso.models import (
    Address,
    Auth,
    Consumption,
    Counter,
    Dashboard,
    Housing,
    Housings,
    Meter,
    MeterInfo,
    User,
)
from myconso.utils import (
    clean_json_ld,
    decode_jwt,
    first_day_of_the_month,
    last_day_of_the_month,
)

P = ParamSpec("P")
T = TypeVar("T")

log = logging.getLogger(__name__)

MYCONSO_API = "https://api.myconso.net"
MYCONSO_USER_AGENT = "MyConso"

TOKEN_EXP_DELAY = 10


def check_auth(
    func: "Callable[Concatenate['MyConsoClient', P], Awaitable[T]]",
) -> "Callable[Concatenate['MyConsoClient', P], Awaitable[T]]":
    """Ensure authentication is initiated or refreshed before calling
    the wrapped method.

    Args:
        func: The async method to wrap.

    Returns:
        The wrapped method with authentication checks.

    """

    async def wrapper(
        self: "MyConsoClient",
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
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
    token_exp: int
    token_iat: int
    counters: list[dict[str, str]]
    housing: str | None
    housings: list[str]
    user: str | None
    lock: asyncio.Lock

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        refresh_token: str | None = None,
        refresh_middleware: bool = True,
    ) -> None:
        """Initialize the API client with authentication parameters.

        Args:
            username: Account email for password-based authentication.
            password: Account password for password-based authentication.
            token: Existing JWT access token for token-based authentication.
            refresh_token: Existing refresh token for token-based authentication.
            refresh_middleware: Whether to enable automatic token refresh middleware.

        Raises:
            ValueError: If neither username/password nor token/refresh_token
                are provided.

        """
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

        middlewares = []
        if refresh_middleware:
            middlewares += [self._auth_refresh_middleware]
        middlewares += [exponential_backoff_middleware]

        self.session = ClientSession(
            base_url=MYCONSO_API,
            headers={"user-agent": MYCONSO_USER_AGENT},
            raise_for_status=True,
            middlewares=middlewares,
            cookie_jar=DummyCookieJar(),
        )

    async def __aenter__(self) -> "MyConsoClient":
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the session."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying aiohttp client session.

        Returns:
            None

        """
        await self.session.close()

    async def _auth_refresh_middleware(
        self, req: ClientRequest, handler: ClientHandlerType
    ) -> ClientResponse:
        """Refresh the access token if it has expired or is close to expiry.

        This aiohttp middleware checks the JWT expiration before each request
        and refreshes the token when needed before attaching the Authorization
        header and forwarding the request.

        Args:
            req: The outgoing aiohttp client request.
            handler: The next handler in the middleware chain.

        Returns:
            The aiohttp client response.

        """
        epoch_now = time.time()
        token = self.token
        if epoch_now >= self.token_exp - TOKEN_EXP_DELAY:
            log.debug(
                "token is expired, refresh it, exp: %s, time: %s",
                self.token_exp,
                epoch_now,
            )
            async with self.lock:
                if token == self.token:
                    res_token = await self.auth_refresh()
                    token = res_token.token

        req.headers["authorization"] = f"Bearer {self.token}"
        res = await handler(req)

        return res

    async def auth(self) -> Auth:
        """Authenticate with username and password to obtain tokens.

        Sends a POST request to /auth with the stored credentials and updates
        the client state with the returned JWT token, refresh token, user
        information, and default housing.

        Returns:
            The parsed authentication response.

        Raises:
            aiohttp.ClientResponseError: If the authentication request fails.

        """
        async with self.session.post(
            "/auth",
            json={
                "email": self.username,
                "password": self.password,
            },
            middlewares=(),
        ) as response:
            res = Auth.model_validate(await response.json())
            self.user = res.user.userIdentifier
            self.housings = res.user.housingIds
            self.housing = res.housing
            self.token = res.token
            self.refresh_token = res.refresh_token
            self.token_exp, self.token_iat = decode_jwt(self.token)

            log.debug("successful authentification for housing: %s", self.housing)

            return res

    async def auth_refresh(self) -> Auth:
        """Force a token refresh using the stored refresh token.

        Sends a POST request to /auth/refresh and updates the client state
        with the new JWT token, refresh token, and user information.

        Returns:
            The parsed authentication response containing the new tokens.

        Raises:
            aiohttp.ClientResponseError: If the refresh request fails.

        """
        async with self.session.post(
            "/auth/refresh",
            json={
                "refresh_token": self.refresh_token,
            },
            middlewares=(),
        ) as response:
            res = Auth.model_validate(await response.json())
            self.user = res.user.userIdentifier
            self.housings = res.user.housingIds
            self.housing = res.housing
            self.token = res.token
            self.refresh_token = res.refresh_token
            self.token_exp, self.token_iat = decode_jwt(self.token)

            self.token_exp, self.token_iat = decode_jwt(self.token)

            log.debug(
                "successful refresh authentification for housing: %s",
                self.housing,
            )

            return res

    @check_auth
    async def get_user(self) -> User:
        """Retrieve information about the authenticated user.

        Returns:
            The user profile data.

        """
        async with self.session.get(f"/secured/users/{self.user}") as res:
            return User.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_address(self, housing: str | None = None) -> Address:
        """Retrieve the postal address for a given housing.

        Args:
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.

        Returns:
            The address data for the specified housing.

        """
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/housing/{housing}/address") as res:
            return Address.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_housings(self) -> Housings:
        """Retrieve all housings associated with the current user.

        Returns:
            A list of housings for the authenticated user.

        """
        async with self.session.get(f"/secured/users/{self.user}/housings") as res:
            return Housings.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_housing(self, housing: str | None = None) -> Housing:
        """Retrieve detailed information about a specific housing.

        Args:
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.

        Returns:
            The housing details.

        """
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/housing/{housing}") as res:
            return Housing.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_dashboard(self, housing: str | None = None) -> Dashboard:
        """Retrieve the consumption dashboard for a given housing.

        Args:
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.

        Returns:
            The dashboard data as displayed in the Myconso app.

        """
        housing = housing if housing else self.housing
        async with self.session.get(f"/secured/consumption/{housing}/dashboard") as res:
            return Dashboard.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_counters(self) -> Counter:
        """List all utility counters across every housing.

        On the first call this method fetches the dashboard for each housing
        and aggregates the counters. Subsequent calls return the cached list.

        Returns:
            A collection of counter items with fluid type, meter type, and unit.

        """
        if not self.counters:
            for housing in self.housings:
                dashboard = await self.get_dashboard(housing)
                for v in dashboard.currentMonth.values:
                    for counter in v.counters:
                        self.counters.append(
                            {
                                "counter": counter,
                                "fluidType": v.fluidType,
                                "meterType": v.meterType,
                                "unit": v.unit,
                                "housing": housing,
                            }
                        )
        return Counter.model_validate(self.counters)

    @check_auth
    async def get_consumption(
        self,
        fluidtype: str,
        housing: str | None = None,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> Consumption:
        """Retrieve daily consumption data for a given fluid type.

        Args:
            fluidtype: The type of fluid (e.g. "waterHot", "waterCold", "heating").
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.
            startdate: Start of the date range. Defaults to the first day of the
                current month if omitted.
            enddate: End of the date range. Defaults to the last day of the
                current month if omitted.

        Returns:
            The consumption data aggregated per day.

        """
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
            return Consumption.model_validate(clean_json_ld(await res.json()))

    @check_auth
    async def get_meter_info(
        self, counter: str, housing: str | None = None
    ) -> MeterInfo | None:
        """Retrieve metadata information for a given counter.

        Args:
            counter: The counter identifier.
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.

        Returns:
            The meter metadata (location, last value, data freshness) if the
            counter is found, otherwise ``None``.

        """
        counters = await self.get_counters()

        housing = housing if housing else self.housing
        for c in counters.root:
            if c.counter == counter:
                async with self.session.get(
                    f"/secured/meter/{housing}/{c.meterType}/{c.counter}/info",
                ) as res:
                    return MeterInfo.model_validate(clean_json_ld(await res.json()))
        return None

    @check_auth
    async def get_meter(
        self,
        counter: str,
        housing: str | None = None,
        startdate: datetime | None = None,
        enddate: datetime | None = None,
    ) -> Meter | None:
        """Retrieve raw meter readings for a given counter over a date range.

        By default the current month is returned when ``startdate`` and
        ``enddate`` are omitted.

        Args:
            counter: The counter identifier.
            housing: The housing identifier. Defaults to the authenticated user's
                default housing if not provided.
            startdate: Start of the date range. Defaults to the first day of the
                current month if omitted.
            enddate: End of the date range. Defaults to the last day of the
                current month if omitted.

        Returns:
            The meter index data if the counter is found, otherwise ``None``.

        """
        if not startdate:
            startdate = first_day_of_the_month()
        if not enddate:
            enddate = last_day_of_the_month()

        counters = await self.get_counters()

        housing = housing if housing else self.housing
        for c in counters.root:
            if c.counter == counter:
                async with self.session.get(
                    f"/secured/meter/{housing}/{c.meterType}/{c.counter}",
                    params={
                        "startDate": startdate.isoformat(timespec="milliseconds"),
                        "endDate": enddate.isoformat(timespec="milliseconds"),
                    },
                ) as res:
                    return Meter.model_validate(clean_json_ld(await res.json()))
        return None
