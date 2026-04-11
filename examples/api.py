import asyncio
import os
from datetime import datetime
from pprint import pprint

from myconso.api import MyConsoClient

MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")


async def main():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        pprint((await c.get_dashboard()).model_dump())
        pprint((await c.get_housing()).model_dump())

        counters = await c.get_counters()
        pprint(counters.model_dump())

        if counters.root:
            pprint(
                (await c.get_meter_info(counter=counters.root[0].counter)).model_dump()
            )

        pprint((await c.get_consumption(fluidtype="waterHot")).model_dump())

        pprint(
            (
                await c.get_consumption(
                    fluidtype="waterHot",
                    startdate=datetime(2025, 12, 1),
                    enddate=datetime(2025, 12, 4),
                )
            ).model_dump()
        )

        if counters.root:
            pprint((await c.get_meter(counter=counters.root[0].counter)).model_dump())

            pprint(
                (
                    await c.get_meter(
                        counter=counters.root[0].counter,
                        startdate=datetime(2025, 12, 1),
                        enddate=datetime(2025, 12, 4),
                    )
                ).model_dump()
            )


asyncio.run(main())
