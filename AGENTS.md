# AGENTS.md - myconso Python SDK

> **Agent-First Documentation**: This file provides context for AI agents working with the myconso Python SDK codebase.

---

## 1. Purpose and Overview

**myconso** is an unofficial, fully asynchronous Python client for the [myconso.net API](https://api.myconso.net) (Proxiserve). It enables users to retrieve utility consumption data (water hot/cold, thermal, etc.) from the Myconso application. his main purpose is to be used with the repository (myconso_ha)[https://github.com/remijouannet/myconso_ha] which is a home assistant integration.

### Key Features

- **Async-First Design**: Built entirely on `aiohttp` for high-performance asynchronous I/O
- **Dual Authentication**: Supports both username/password and token/refresh_token flows
- **Automatic Token Refresh**: JWT tokens are automatically refreshed before expiration using middleware
- **Resilient Retry Logic**: Exponential backoff middleware handles rate limiting (HTTP 429/503)
- **Type-Safe**: Full type annotations using modern Python 3.10+ syntax
- **CLI Support**: Full-featured command-line interface via `myconsocli`

### Project Metadata

| Attribute | Value |
|-----------|-------|
| Version | 0.0.7 |
| Python | >= 3.10 |
| Package Manager | `uv` |
| License | (see repository) |
| Repository | https://github.com/remijouannet/myconso.py |

---

## 2. Architecture

### High-Level Structure

```
myconso/
├── api.py          # Core API client (MyConsoClient)
├── middlewares.py  # aiohttp middleware (backoff, auth refresh)
├── utils.py        # Utilities (JWT, dates, JSON-LD cleaning)
└── cli.py          # Command-line interface
```

### Async Design Patterns

#### Context Manager Pattern
All API calls use async context managers for proper resource management:

```python
async with MyConsoClient(username="...", password="...") as client:
    data = await client.get_dashboard()
# Session auto-closes on exit
```

#### Middleware Stack
The client uses a layered middleware architecture:

```
Request → Auth Refresh Middleware → Exponential Backoff Middleware → HTTP Handler
                                            ↓
Response ← Auth Refresh Middleware ← Exponential Backoff Middleware ← HTTP Response
```

1. **Auth Refresh Middleware** (`_auth_refresh_middleware`): Checks JWT expiration before each request, refreshes if needed
2. **Exponential Backoff Middleware** (`exponential_backoff_middleware`): Retries on rate limiting with exponential delay

#### Thread-Safe Authentication
Uses `asyncio.Lock()` to prevent concurrent token refresh attempts:

```python
async with self.lock:
    if token == self.token:  # Double-check pattern
        await self.auth_refresh()
```

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `aiohttp` | Async HTTP client framework |
| `aiohttp-retry>=2.9.1` | Retry logic utilities |
| `pyjwt[crypto]` | JWT token encoding/decoding |

### Authentication Flow

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Credentials   │────→│    auth()    │────→│  Token + JWT    │
│  (user/pass)    │     └──────────────┘     │  (exp, iat)     │
└─────────────────┘                          └────────┬────────┘
                                                      │
┌─────────────────┐     ┌──────────────┐             │
│ Token/Refresh   │────→│auth_refresh()│←────────────┘
│   (re-auth)     │     └──────────────┘     (auto on expiry)
└─────────────────┘
```

---

## 3. Modern Python Practices

### Package Management with `uv`

This project uses `uv` for fast, reliable Python package management:

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run tests
uv run pytest

# Run CLI
uv run myconsocli --help
```

The `uv.lock` file ensures reproducible builds across environments.

### Linting and Formatting with `ruff`

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
include = ["tests/*.py", "myconso/*.py"]

[tool.ruff.lint]
select = [
    "ASYNC",  # flake8-async
    "E",      # pycodestyle
    "F",      # Pyflakes
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "SIM",    # flake8-simplify
    "I",      # isort
    "RUF",    # ruff-specific
    "Q",      # flake8-quotes
    "PL",     # pylint
]
```

Run linting:
```bash
uv run ruff check .
uv run ruff format .
```

### Type Hints

Uses modern Python 3.10+ union syntax (`X | Y` instead of `Optional[X]` or `Union[X, Y]`):

```python
# Union types
username: str | None = None
startdate: datetime | None = None

# Return types
async def get_user(self) -> dict:
async def get_meter_info(...) -> dict | None:

# Type vars with TracebackType
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    traceback: TracebackType | None,
) -> None:
```

Type checking with mypy:
```bash
uv run mypy myconso/
```

### Pre-commit Hooks

The `.pre-commit-config.yaml` enforces code quality:

- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Ruff check and format
- MyPy type checking

Install hooks:
```bash
uv run pre-commit install
```

### Async Patterns

#### Decorator for Auth Check
```python
def check_auth(func):
    async def wrapper(self, *args, **kwargs):
        if not self.token and (self.username and self.password):
            async with self.lock:
                await self.auth()
        elif not self.housing and self.token and self.refresh_token:
            async with self.lock:
                await self.auth_refresh()
        return await func(self, *args, **kwargs)
    return wrapper
```

#### Token Expiration Handling
```python
TOKEN_EXP_DELAY = 10  # seconds before actual expiry

epoch_now = time.time()
if epoch_now >= self.token_exp - TOKEN_EXP_DELAY:
    async with self.lock:
        # Refresh token
```

---

## 4. Agentic Workflows

### Adding a New API Endpoint

When adding a new API method to `MyConsoClient`:

1. **Add the method** in `myconso/api.py`:
```python
@check_auth
async def get_new_resource(self, param: str) -> dict:
    async with self.session.get(f"/secured/new/{param}") as res:
        return clean_json_ld(await res.json())
```

2. **Add type hints** for all parameters and return types

3. **Add tests** in `tests/test_api.py`:
```python
@pytest.mark.asyncio
async def test_get_new_resource():
    async with MyConsoClient(token="...", refresh_token="...") as c:
        result = await c.get_new_resource("test")
        assert "expected_key" in result
```

4. **Run linting and type checking**:
```bash
uv run ruff check myconso/api.py
uv run mypy myconso/api.py
```

### Adding Middleware

To add custom middleware:

1. Create middleware function in `myconso/middlewares.py`:
```python
async def custom_middleware(
    req: ClientRequest, 
    handler: ClientHandlerType
) -> ClientResponse:
    # Pre-processing
    req.headers["X-Custom-Header"] = "value"
    
    # Call handler
    res = await handler(req)
    
    # Post-processing
    if res.status == 418:  # I'm a teapot
        raise CustomError("Unexpected teapot")
    
    return res
```

2. Register in `MyConsoClient.__init__`:
```python
middlewares = []
if refresh_middleware:
    middlewares += [self._auth_refresh_middleware]
middlewares += [exponential_backoff_middleware]
middlewares += [custom_middleware]  # Add here
```

### Testing Patterns

#### Mocking with AioHTTPTestCase
```python
class TestMyEndpoint(AioHTTPTestCase):
    async def get_application(self):
        async def handler(request):
            return web.json_response({"data": "test"})
        
        app = web.Application()
        app.router.add_get("/endpoint", handler)
        return app

    async def test_endpoint(self):
        async with MyConsoClient(token="...", refresh_token="...") as c:
            # Replace session with test server
            await c.session.close()
            c.session = ClientSession(
                base_url=self.client.make_url(""),
                middlewares=(...),
            )
            result = await c.get_resource()
            assert result["data"] == "test"
```

#### Environment-Based Integration Tests
Tests in `tests/test_api.py` require environment variables:
```bash
export MYCONSO_EMAIL="user@example.com"
export MYCONSO_PASSWORD="secret"
export MYCONSO_HOUSING="12345"
uv run pytest tests/test_api.py
```

### Documentation Generation

When modifying public APIs, ensure:
1. Docstrings follow Google/NumPy style
2. Examples are added to `examples/`
3. CLI help text is updated in `myconso/cli.py`
4. README.md is updated with new features

---

## 5. Examples

### Example 1: Basic Usage with Username/Password

```python
import asyncio
import os
from myconso.api import MyConsoClient

MYCONSO_EMAIL = os.getenv("MYCONSO_EMAIL")
MYCONSO_PASSWORD = os.getenv("MYCONSO_PASSWORD")

async def main():
    async with MyConsoClient(
        username=MYCONSO_EMAIL, 
        password=MYCONSO_PASSWORD
    ) as client:
        # Get user info
        user = await client.get_user()
        print(f"User: {user['email']}")
        
        # Get consumption dashboard
        dashboard = await client.get_dashboard()
        for value in dashboard["currentMonth"]["values"]:
            print(f"{value['fluidType']}: {value['value']} {value['unit']}")
        
        # List all counters
        counters = await client.get_counters()
        for counter in counters:
            print(f"Counter {counter['counter']}: {counter['fluidType']}")

asyncio.run(main())
```

### Example 2: Token-Based Auth with Date Queries

```python
import asyncio
from datetime import datetime
from myconso.api import MyConsoClient

async def main():
    # Use existing tokens (useful for long-running apps)
    async with MyConsoClient(
        token="eyJ0eXAiOiJKV1QiLCJhbGc...",
        refresh_token="FjgyrAD4aw4f3e59snkv..."
    ) as client:
        # Get consumption for specific date range
        consumption = await client.get_consumption(
            fluidtype="waterHot",
            startdate=datetime(2025, 12, 1),
            enddate=datetime(2025, 12, 31)
        )
        
        for reading in consumption.get("consumptionData", []):
            print(f"{reading['date']}: {reading['value']} m³")
        
        # Get meter readings for a specific counter
        meter_data = await client.get_meter(
            counter="ED379533C5",
            startdate=datetime(2025, 11, 1),
            enddate=datetime(2025, 11, 30)
        )
        print(f"Meter info: {meter_data}")

asyncio.run(main())
```

### Example 3: Error Handling and CLI Usage

```python
import asyncio
import logging
from aiohttp import ClientResponseError
from myconso.api import MyConsoClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    try:
        async with MyConsoClient(
            username="user@example.com",
            password="wrong_password"
        ) as client:
            await client.get_dashboard()
    except ClientResponseError as e:
        if e.status == 401:
            print("Authentication failed: Invalid credentials")
        elif e.status == 429:
            print("Rate limited: Too many requests")
        else:
            print(f"API error: {e.status} - {e.message}")
    except ValueError as e:
        print(f"Configuration error: {e}")

asyncio.run(main())
```

**CLI Usage:**
```bash
# Get dashboard via CLI
myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD --dashboard

# Get consumption with date range
myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD \
    --consumption waterHot --start-date 2025-12-01 --end-date 2025-12-31

# Get meter info
myconsocli --email $MYCONSO_EMAIL --password $MYCONSO_PASSWORD \
    --meter-info 123456789
```

---

## 6. Testing

Very important, do not try to run any tests if the following Environnement variable are not set MYCONSO_EMAIL, MYCONSO_PASSWORD, MYCONSO_HOUSING.

### Test Structure

```
tests/
├── test_api.py              # Integration tests (requires API access)
├── test_backoff.py          # Middleware retry logic tests
└── test_refresh_token.py    # Token refresh mechanism tests
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_backoff.py

# Run with debug output
uv run pytest -v --log-cli-level=DEBUG

# Run only mocked tests (no API calls)
uv run pytest tests/test_backoff.py tests/test_refresh_token.py
```

### Documentation

Here is the documentation to use pytest with pytest-aiohttp, [pytest-aiohttp](https://docs.aiohttp.org/en/stable/testing.html)

### Async Test Patterns

#### Basic Async Test
```python
import pytest
from myconso.api import MyConsoClient

@pytest.mark.asyncio
async def test_get_user():
    async with MyConsoClient(token="...", refresh_token="...") as c:
        user = await c.get_user()
        assert "email" in user
```

#### Mocking aiohttp with AioHTTPTestCase
```python
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

class TestAPI(AioHTTPTestCase):
    async def get_application(self):
        async def mock_handler(request):
            return web.json_response({"data": "test"})
        
        app = web.Application()
        app.router.add_get("/endpoint", mock_handler)
        return app

    async def test_with_mock_server(self):
        # self.client is the test server client
        url = self.client.make_url("/endpoint")
        # Use with MyConsoClient
```

#### Testing Middleware
```python
@pytest.mark.asyncio
async def test_exponential_backoff():
    # Create mock request/response
    from aiohttp import ClientRequest, ClientResponse
    
    # Test retry logic on 429 responses
    # See tests/test_backoff.py for full example
```

### Environment Variables for Integration Tests

Integration tests in `tests/test_api.py` require:

| Variable | Description |
|----------|-------------|
| `MYCONSO_EMAIL` | Account email |
| `MYCONSO_PASSWORD` | Account password |
| `MYCONSO_HOUSING` | Housing ID for testing |

Set these before running tests:
```bash
export MYCONSO_EMAIL="test@example.com"
export MYCONSO_PASSWORD="testpassword"
export MYCONSO_HOUSING="12345678"
uv run pytest tests/test_api.py -v
```

### Test Best Practices

1. **Use pytest-asyncio**: All async tests must use `@pytest.mark.asyncio`
2. **Close sessions**: Always use `async with` or manually close sessions
3. **Mock external APIs**: Use `AioHTTPTestCase` for unit tests
4. **Test middleware**: Mock HTTP responses to test retry logic
5. **Check token refresh**: Use short-lived JWT tokens in tests

### Code Quality Checks

Before committing, run all quality checks:

```bash
# Linting
uv run ruff check myconso/ tests/

# Formatting
uv run ruff format myconso/ tests/

# Type checking
uv run mypy myconso/

# Tests
uv run pytest

# Pre-commit hooks
uv run pre-commit run --all-files
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check | `uv run mypy myconso/` |
| Run CLI | `uv run myconsocli --help` |
| Pre-commit | `uv run pre-commit run --all-files` |

---

**Last Updated**: 2026-04-11  
**Agent Note**: When modifying this SDK, maintain async-first patterns, use type hints, and ensure all tests pass with `uv run pytest`.
