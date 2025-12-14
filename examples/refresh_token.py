import asyncio
import os
from pprint import pprint

from myconso.api import MyConsoClient

MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")


async def main():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        res = await c.auth()
        pprint(res)
        token = res["token"]
        refresh_token = res["refresh_token"]

    async with MyConsoClient(token=token, refresh_token=refresh_token) as c:
        pprint(await c.get_housing())


asyncio.run(main())
