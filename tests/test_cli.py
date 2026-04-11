from __future__ import annotations

import json
import os
import sys

import pytest

import myconso.cli as cli_mod

# Retrieve required environment variables
MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")
MYCONSO_HOUSING = os.getenv("MYCONSO_HOUSING")

# Skip all tests in this module if any variable is missing
pytestmark = pytest.mark.skipif(
    not (MYCONSO_EMAIL and MYCONSO_PASSWORD and MYCONSO_HOUSING),
    reason="Missing MyConso environment variables",
)


@pytest.fixture
def run_cli(monkeypatch, capsys):
    """Helper to invoke the CLI with a list of arguments and return parsed JSON."""

    def _run(args: list[str]):
        # Ensure the script name is present (argv[0])
        monkeypatch.setattr(sys, "argv", ["myconsocli", *args])
        # Execute the CLI entry point
        cli_mod.main()
        captured = capsys.readouterr()
        # The CLI prints pretty-printed JSON; parse it for assertions
        return json.loads(captured.out)

    return _run


def test_cli_auth(run_cli):
    result = run_cli(
        [
            "--email",
            MYCONSO_EMAIL,
            "--password",
            MYCONSO_PASSWORD,
            "--auth",
        ]
    )
    assert isinstance(result, dict)
    assert "token" in result
    assert "refresh_token" in result


def test_cli_dashboard(run_cli):
    result = run_cli(
        [
            "--email",
            MYCONSO_EMAIL,
            "--password",
            MYCONSO_PASSWORD,
            "--dashboard",
            "--housing-id",
            MYCONSO_HOUSING,
        ]
    )
    assert isinstance(result, dict)
    assert "currentMonth" in result


def test_cli_user(run_cli):
    result = run_cli(
        [
            "--email",
            MYCONSO_EMAIL,
            "--password",
            MYCONSO_PASSWORD,
            "--user",
        ]
    )
    assert isinstance(result, dict)
    # The API returns a user object where "id" matches the email address
    assert result.get("id") == MYCONSO_EMAIL


def test_cli_counters(run_cli):
    result = run_cli(
        [
            "--email",
            MYCONSO_EMAIL,
            "--password",
            MYCONSO_PASSWORD,
            "--counters",
        ]
    )
    assert isinstance(result, list)
    # At least one counter dict should contain a "counter" key
    assert any(isinstance(item, dict) and "counter" in item for item in result)
