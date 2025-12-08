import asyncio
import logging

import aiohttp
from aiohttp import ClientHandlerType, ClientRequest, ClientResponse

log = logging.getLogger(__name__)

BACKOFF_STATUS_CODES = {429, 503}
BACKOFF_MAX_RETRIES = 3
BACKOFF_BASE_DELAY = 1.0,
BACKOFF_MAX_DELAY = 60.0

async def exponential_backoff_middleware(
        req: ClientRequest, handler: ClientHandlerType
) -> ClientResponse:
    log.debug("middleware exponential_backoff_middleware")
    retry_count = 0

    while retry_count <= BACKOFF_MAX_RETRIES:
        resp = await handler(req)
        if retry_count < BACKOFF_MAX_RETRIES and resp.status in BACKOFF_STATUS_CODES:
            delay = self._calculate_delay(
                    retry_count, BACKOFF_BASE_DELAY, BACKOFF_MAX_DELAY
                )
            log.debug(
                    "retry backoff for %s, sleep for %ss", resp.status, str(delay)
                )
            await asyncio.sleep(min(BACKOFF_BASE_DELAY * (2 ** (retry_count - 1)), BACKOFF_MAX_DELAY))
            retry_count += 1
        else:
            return resp
