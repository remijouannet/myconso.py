
# Unofficial async python client for myconso (proxiserve) API

Unofficial fully asynchronous API client for the myconso api behind the [Myconso application](https://play.google.com/store/apps/details?id=fr.proxiserve.myconso&hl=fr). To easily retrieve information about your counters (waterhot, watercold, thermal, ...)

## Installation

```bash
pip install myconso 
```

## Getting started

### Client
```python
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
```
### cli

```bash
.venv/bin/myconsocli --help
usage: myconsocli [-h] [--debug] --email EMAIL --password PASSWORD [--auth] [--dashboard] [--counters] [--housing] [--user] [--meter-info METER_INFO]
                  [--meter METER] [--consumption CONSUMPTION] [--start-date START_DATE] [--end-date END_DATE]

myconso cli

options:
  -h, --help            show this help message and exit
  --debug               enable debug logging
  --email EMAIL         email
  --password PASSWORD   password
  --auth                POST auth/
  --dashboard           GET /secured/consumption/{housing}/dashboard
  --counters            List counters from dashboard
  --housing             GET /secured/housing/{housing}
  --user                GET /secured/users/{user}
  --meter-info METER_INFO
                        GET /secured/meter/{housing}/{fluidType}/{counter}/info
  --meter METER         GET /secured/meter/{housing}/{fluidType}/{counter}
  --consumption CONSUMPTION
                        /secured/consumption/{housing}/{fluidtype}/day
  --start-date START_DATE
                        start date for consumption and meter
  --end-date END_DATE   end date for consumption and meter

.venv/bin/myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD --dashboard
{'currentMonth': {'endDate': '2025-12-13T12:01:00+00:00',
                  'startDate': '2025-12-01T17:25:19+00:00',
                  'values': [{'counters': ['123456'],
                              'fluidType': 'waterHot',
                              'maxValue': 1.0,
                              'meterType': 'waterHot',
                              'minValue': 1.0,
                              'unit': 'm3',
                              'value': 1.0,
                              'weightedValue': None},
                             }

.venv/bin/myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD --meter-info 123456789
{}

.venv/bin/myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD --meter 123456789 --start-date 2025-11-01 --end-date 2025-11-05
{}
```
