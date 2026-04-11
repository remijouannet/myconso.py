"""Pytest fixtures and helpers for myconso tests.

This module provides fixtures and helper functions to create valid mock responses
that pass pydantic model validation.
"""

from __future__ import annotations

import time
from typing import Any

import jwt


def create_auth_response(
    token_exp: int | None = None,
    housing: str = "7552325423",
    refresh_token: str = "FjgyrAD4aw4f3e59snkvsejhn4yywf7w",
) -> dict[str, Any]:
    """Create a valid auth response that passes pydantic validation.

    Args:
        token_exp: Token expiration time in seconds from now. Defaults to 3600.
        housing: Housing ID. Defaults to "7552325423".
        refresh_token: Refresh token string.

    Returns:
        Dictionary with all required fields for Auth and User models.
    """
    if token_exp is None:
        token_exp = int(time.time() + 3600)

    token_iat = int(time.time())

    return {
        "company": "test",
        "housing": housing,
        "refresh_token": refresh_token,
        "token": jwt.encode(
            {"exp": token_exp, "iat": token_iat},
            "secret",
            algorithm="HS256",
        ),
        "user": {
            "email": "test@test.com",
            "password": "hashed_password",
            "cgu": True,
            "cgdatadaily": True,
            "firstname": "Test",
            "lastname": "User",
            "cgAcceptedAt": "2024-01-01T00:00:00+00:00",
            "lastConnected": None,
            "isActive": True,
            "mobileNotification": True,
            "emailNotification": True,
            "consumptionGoal": {"name": "goal", "value": "100"},
            "isOnboarded": True,
            "roles": ["ROLE_USER"],
            "userIdentifier": "test@test.com",
            "id": 12345,
            "userDeviceTokens": [],
            "housingIds": [housing],
            "housingNames": ["Test Housing"],
            "passwordResetCode": None,
            "passwordResetLimitDate": None,
            "createdAt": "2024-01-01T00:00:00+00:00",
            "updatedAt": "2024-01-01T00:00:00+00:00",
        },
    }


def create_dashboard_response(
    housing: str = "7552325423",
) -> dict[str, Any]:
    """Create a valid dashboard response that passes pydantic validation.

    Args:
        housing: Housing ID for the counters. Defaults to "7552325423".

    Returns:
        Dictionary with all required fields for Dashboard model.
    """
    return {
        "currentMonth": {
            "endDate": "2025-12-07T12:01:00+00:00",
            "startDate": "2025-12-01T16:53:16+00:00",
            "values": [
                {
                    "counters": ["ED379533C5"],
                    "fluidType": "waterHot",
                    "maxValue": 1.0,
                    "meterType": "waterHot",
                    "minValue": 25.0,
                    "unit": "m3",
                    "value": 1.0,
                    "weightedValue": None,
                }
            ],
        },
        "lastMonth": {
            "endDate": "2025-11-30T12:00:00+00:00",
            "startDate": "2025-11-01T16:53:15+00:00",
            "values": [
                {
                    "counters": ["ED379533C5"],
                    "fluidType": "waterHot",
                    "maxValue": 1.0,
                    "meterType": "waterHot",
                    "minValue": 25.0,
                    "unit": "m3",
                    "value": 1.0,
                    "weightedValue": None,
                }
            ],
        },
    }


def create_housing_response(
    housing_id: str = "7552325423",
) -> dict[str, Any]:
    """Create a valid housing response that passes pydantic validation.

    Args:
        housing_id: Housing ID. Defaults to "7552325423".

    Returns:
        Dictionary with all required fields for Housing model.
    """
    return {
        "housingId": housing_id,
        "name": "Logement 10",
        "entryDate": "2024-05-30T00:00:00+00:00",
        "surface": 40,
        "numberInhabitants": 2,
        "housingType": "t2",
        "energyLabel": "A",
        "company": "proxiserve",
        "proofStatus": "validated",
        "isActive": True,
        "proofUploadDate": "2025-04-05T20:26:24+00:00",
        "createdAt": "2025-04-02T10:10:58+00:00",
    }
