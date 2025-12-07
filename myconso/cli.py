import argparse
import asyncio
import logging
from pprint import pprint

from myconso.api import MyConso

log = logging.getLogger(__name__)


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
        "--action",
        dest="action",
        type=str,
        required=True,
        help="action",
    )

    args = parser.parse_args()

    async with MyConso(username=args.email, password=args.password) as myconso:
        await myconso.login()
        if args.action == "dashboard":
            pprint(await myconso.get_dashboard())
        elif args.action == "counters":
            pprint(await myconso.get_counters())
        elif args.action == "housing":
            pprint(await myconso.get_housing())
        elif args.action == "user":
            pprint(await myconso.get_user())


def main():
    asyncio.run(cli())
