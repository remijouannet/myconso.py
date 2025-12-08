import argparse
import asyncio
import datetime
import logging
from pprint import pprint

from myconso.api import MyConso

logging.basicConfig(level=logging.DEBUG)


async def cli():
    parser = argparse.ArgumentParser(description="myconso cli")
    parser.add_argument(
        "--email",
        dest="email",
        type=str,
        required=True,
        help="email",
    )
    parser.add_argument(
        "--password",
        dest="password",
        type=str,
        required=True,
        help="password",
    )
    parser.add_argument(
        "--login",
        dest="login",
        default=False,
        action="store_true",
        help="action",
    )
    parser.add_argument(
        "--dashboard",
        dest="dashboard",
        default=False,
        action="store_true",
        help="action",
    )
    parser.add_argument(
        "--counters",
        dest="counters",
        default=False,
        action="store_true",
        help="action",
    )
    parser.add_argument(
        "--housing",
        dest="housing",
        default=False,
        action="store_true",
        help="action",
    )
    parser.add_argument(
        "--user",
        dest="user",
        default=False,
        action="store_true",
        help="action",
    )
    parser.add_argument(
        "--meter-info",
        dest="meter_info",
        default=None,
        type=str,
        help="action",
    )
    parser.add_argument(
        "--meter",
        dest="meter",
        default=None,
        type=str,
        help="action",
    )
    parser.add_argument(
        "--consumption",
        dest="consumption",
        default=None,
        type=str,
        help="action",
    )
    parser.add_argument(
        "--start-date",
        dest="start_date",
        default=None,
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="action",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date",
        default=None,
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="action",
    )

    args = parser.parse_args()

    async with MyConso(username=args.email, password=args.password) as myconso:
        if args.login:
            pprint(await myconso.login())
        elif args.dashboard:
            pprint(await myconso.get_dashboard())
        elif args.counters:
            pprint(await myconso.get_counters())
        elif args.housing:
            pprint(await myconso.get_housing())
        elif args.user:
            pprint(await myconso.get_user())
        elif args.meter_info:
            pprint(await myconso.get_meter_info(args.meter_info))
        elif args.meter:
            pprint(await myconso.get_meter(args.meter, args.start_date, args.end_date))
        elif args.consumption:
            pprint(
                await myconso.get_consumption(
                    args.consumption, args.start_date, args.end_date
                )
            )
        else:
            pprint(await myconso.get_dashboard())


def main():
    asyncio.run(cli())
