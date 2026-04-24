import calendar
from datetime import datetime, timezone
from typing import Any

import jwt


def clean_json_ld(obj: dict[str, Any]) -> dict[str, Any]:
    """Remove JSON-LD metadata keys from a dictionary.

    The API returns JSON-LD objects that may contain keys starting with ``@``
    (e.g. ``@context``, ``@type``). These fields are not needed by the client
    and are stripped out before parsing.

    Args:
        obj: The dictionary returned by the API.

    Returns:
        The dictionary with JSON-LD keys removed.

    """
    if isinstance(obj, dict):
        keys_to_pop = [key for key in obj if key.startswith("@")]
        for key in keys_to_pop:
            obj.pop(key, None)
    return obj


def decode_jwt(token: str) -> tuple[int, int]:
    """Decode a JWT token and return the expiration and issued-at timestamps.

    Args:
        token: The JWT token string.

    Returns:
        A tuple of (expiration_timestamp, issued_at_timestamp).

    """
    token_jwt = jwt.decode(
        token,
        algorithms=["RS256"],
        key="",
        options={"verify_signature": False},
    )
    return (token_jwt["exp"], token_jwt["iat"])


def last_day_of_the_month() -> datetime:
    """Return the last day of the current month as a UTC datetime.

    Returns:
        A datetime object set to 23:59:59 on the last day of the current month.

    """
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
    """Return the first day of the current month as a UTC datetime.

    Returns:
        A datetime object set to midnight on the first day of the current month.

    """
    return datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
