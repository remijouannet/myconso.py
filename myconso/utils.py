import calendar
from datetime import datetime, timezone

import jwt


def decode_jwt(token):
    token_jwt = jwt.decode(
        token,
        algorithms=["RS256"],
        key=None,
        options={"verify_signature": False},
    )
    return token_jwt["exp"], token_jwt["iat"]


def last_day_of_the_month():
    # last day of the current month
    return (
        datetime.now(timezone.utc)
        .replace(
            day=calendar.monthrange(
                datetime.now(timezone.utc).year,
                datetime.now(timezone.utc).month,
            )[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=0,
        )
        .isoformat(timespec="milliseconds")
    )


def first_day_of_the_month():
    # first day of the current month
    return (
        datetime.now(timezone.utc)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .isoformat(timespec="milliseconds")
    )
