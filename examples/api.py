import asyncio
import os
from datetime import datetime
from pprint import pprint

from myconso.api import MyConsoClient

MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")


async def main():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        pprint(await c.get_dashboard())
        pprint(await c.get_housing())

        ctrs = await c.get_counters()
        pprint(ctrs)

        pprint(await c.get_meter_info(counter=ctrs[0]["counter"]))

        pprint(await c.get_consumption(fluidtype="waterHot"))

        pprint(
            await c.get_consumption(
                fluidtype="waterHot",
                startdate=datetime(2025, 12, 1),
                enddate=datetime(2025, 12, 4),
            )
        )

        pprint(await c.get_meter(counter=ctrs[0]["counter"]))

        pprint(
            await c.get_meter(
                counter=ctrs[0]["counter"],
                startdate=datetime(2025, 12, 1),
                enddate=datetime(2025, 12, 4),
            )
        )


asyncio.run(main())
