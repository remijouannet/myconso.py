"""Tests for typed model wrappers in MyConsoClient.

These tests verify that the API methods return the appropriate Pydantic models
and that the model fields contain expected data.
"""

from __future__ import annotations

import os

import pytest

from myconso.api import MyConsoClient
from myconso.models import (
    Consumption,
    Counter,
    Dashboard,
    Meter,
    MeterInfo,
    User,
)

MYCONSO_HOUSING = os.getenv("MYCONSO_HOUSING")
MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")

# Skip all tests in this module if any required variable is missing
pytestmark = pytest.mark.skipif(
    not (MYCONSO_EMAIL and MYCONSO_PASSWORD and MYCONSO_HOUSING),
    reason="Missing MyConso environment variables",
)


@pytest.mark.asyncio
async def test_get_user():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        await c.auth()
        user = await c.get_user()
        assert isinstance(user, User)
        assert user.id == MYCONSO_EMAIL


@pytest.mark.asyncio
async def test_get_dashboard():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        await c.auth()
        dashboard = await c.get_dashboard()
        assert isinstance(dashboard, Dashboard)
        # Verify nested structure has expected attributes
        assert hasattr(dashboard.currentMonth, "startDate")
        assert hasattr(dashboard.lastMonth, "startDate")


@pytest.mark.asyncio
async def test_get_counters():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        await c.auth()
        counters = await c.get_counters()
        assert isinstance(counters, Counter)
        # Counter is a RootModel; the list of items is stored in .root
        assert isinstance(counters.root, list)
        assert len(counters.root) > 0
        first = counters.root[0]
        assert hasattr(first, "counter")
        assert hasattr(first, "fluidType")


@pytest.mark.asyncio
async def test_get_consumption():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        await c.auth()
        # Use a common fluid type; adjust if needed
        consumption = await c.get_consumption("waterHot")
        assert isinstance(consumption, Consumption)
        assert isinstance(consumption.consumptions, list)
        assert len(consumption.consumptions) > 0
        first = consumption.consumptions[0]
        assert hasattr(first, "date")
        assert hasattr(first, "value")


@pytest.mark.asyncio
async def test_get_meter_info_and_meter():
    async with MyConsoClient(username=MYCONSO_EMAIL, password=MYCONSO_PASSWORD) as c:
        await c.auth()
        counters = await c.get_counters()
        # Ensure we have at least one counter to test with
        assert len(counters.root) > 0
        counter_id = counters.root[0].counter

        meter_info = await c.get_meter_info(counter_id)
        assert isinstance(meter_info, MeterInfo)
        assert hasattr(meter_info, "location")

        meter = await c.get_meter(counter_id)
        assert isinstance(meter, Meter)
        assert isinstance(meter.indexes, list)
        # The list may be empty depending on data; just verify type
        if meter.indexes:
            first = meter.indexes[0]
            assert hasattr(first, "date")
            assert hasattr(first, "value")
