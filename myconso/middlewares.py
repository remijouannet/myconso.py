import asyncio
import logging
import random

from aiohttp import ClientHandlerType, ClientRequest, ClientResponse

log = logging.getLogger(__name__)

BACKOFF_STATUS_CODES = {429, 503}
BACKOFF_MAX_RETRIES = 2
BACKOFF_FACTOR = 2.0
BACKOFF_MAX_DELAY = 60.0
BACKOFF_JITTER = 2


async def exponential_backoff_middleware(
    req: ClientRequest, handler: ClientHandlerType
) -> ClientResponse:
    retry_count = 1

    res = await handler(req)
    while retry_count <= BACKOFF_MAX_RETRIES:
        if retry_count < BACKOFF_MAX_RETRIES and res.status in BACKOFF_STATUS_CODES:
            delay = round(
                min(BACKOFF_FACTOR * (2**retry_count), BACKOFF_MAX_DELAY)
                + random.uniform(0, BACKOFF_JITTER),
                3,
            )
            log.debug("retry backoff for %s, sleep for %ss", res.status, str(delay))
            await asyncio.sleep(delay)
            retry_count += 1
            res = await handler(req)
        else:
            break
    return res
