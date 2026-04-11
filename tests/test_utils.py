from __future__ import annotations

import json
import os
import pytest
import jwt

import myconso.utils as utils


def test_clean_json_ld_removes_at_keys():
    data = {"@id": "123", "@type": "Thing", "name": "test"}
    cleaned = utils.clean_json_ld(data.copy())
    assert "@id" not in cleaned
    assert "@type" not in cleaned
    assert cleaned == {"name": "test"}


def test_clean_json_ld_no_at_keys():
    data = {"name": "test", "value": 42}
    cleaned = utils.clean_json_ld(data.copy())
    assert cleaned == data


def test_decode_jwt_monkeypatch(monkeypatch):
    payload = {"exp": 12345, "iat": 67890}

    def fake_decode(*args, **kwargs):
        return payload

    monkeypatch.setattr(utils.jwt, "decode", fake_decode)
    exp, iat = utils.decode_jwt("dummy-token")
    assert exp == payload["exp"]
    assert iat == payload["iat"]


def test_first_and_last_day_of_month(monkeypatch):
    # Fixed datetime: 2025-02-15 12:34:56 UTC
    fixed_dt = utils.datetime(2025, 2, 15, 12, 34, 56, tzinfo=utils.timezone.utc)

    # Create a simple wrapper class with a classmethod now() returning the fixed datetime
    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            return fixed_dt

    # Patch the datetime class used in utils to our wrapper
    monkeypatch.setattr(utils, "datetime", FixedDateTime)
    first = utils.first_day_of_the_month()
    assert first.day == 1
    assert first.hour == 0
    assert first.minute == 0
    assert first.second == 0
    assert first.microsecond == 0
    assert first.tzinfo == utils.timezone.utc

    last = utils.last_day_of_the_month()
    # February 2025 has 28 days
    assert last.day == 28
    assert last.hour == 23
    assert last.minute == 59
    assert last.second == 59
    assert last.microsecond == 0
    assert last.tzinfo == utils.timezone.utc
