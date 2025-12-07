from __future__ import annotations

import json
import os

import pytest
from pytest_asyncio import fixture
import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()
from pprint import pprint
from myconso.api import MyConso

class TestMyConsoClient:
    @pytest.mark.asyncio
    async def test_get_dashboard(self):
        async with MyConso(os.getenv("MYCONSO_EMAIL"), os.getenv("MYCONSO_PASSWORD")) as c:
            await c.get_dashboard()
