import calendar
from datetime import datetime, timezone

import jwt


def clean_json_ld(obj: dict) -> dict:
    # json-ld add keys that starts with @
    # we don't need thoses, pop them
    if isinstance(obj, dict):
        keys_to_pop = [key for key in obj if key.startswith("@")]
        for key in keys_to_pop:
            obj.pop(key, None)
    return obj


def decode_jwt(token: str) -> tuple[int, int]:
    token_jwt = jwt.decode(
        token,
        algorithms=["RS256"],
        key="",
        options={"verify_signature": False},
    )
    return (token_jwt["exp"], token_jwt["iat"])


def last_day_of_the_month() -> datetime:
    # last day of the current month
    return datetime.now(timezone.utc).replace(
        day=calendar.monthrange(
            datetime.now(timezone.utc).year,
            datetime.now(timezone.utc).month,
        )[1],
        hour=23,
        minute=59,
        second=59,
        microsecond=0,
    )


def first_day_of_the_month() -> datetime:
    # first day of the current month
    return datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
