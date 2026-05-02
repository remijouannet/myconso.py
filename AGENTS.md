# AGENTS.md - myconso Python SDK

> **Agent-First Documentation**: This file provides context for AI agents working with the myconso Python SDK codebase.

---

## 1. Purpose and Overview

**myconso** is an unofficial, fully asynchronous Python client for the [myconso.net API](https://api.myconso.net) (Proxiserve). It enables users to retrieve utility consumption data (water hot/cold, thermal, etc.) from the Myconso application. Its main purpose is to be used with the repository [myconso_ha](https://github.com/remijouannet/myconso_ha) which is a Home Assistant integration.

| Attribute | Value |
|-----------|-------|
| Version | 0.0.7 |
| Python | >= 3.10 |
| Package Manager | `uv` |
| License | (see repository) |
| Repository | https://github.com/remijouannet/myconso.py |

---

## 2. Architecture

```
myconso/
├── api.py          # Core API client (MyConsoClient)
├── middlewares.py  # aiohttp middleware (backoff, auth refresh)
├── utils.py        # Utilities (JWT, dates, JSON-LD cleaning)
└── cli.py          # Command-line interface
```

### Async Design Patterns

- **Context Manager Pattern**: All API calls use async context managers for proper resource management.
- **Middleware Stack**:
  ```
  Request → Auth Refresh Middleware → Exponential Backoff Middleware → HTTP Handler
                                              ↓
  Response ← Auth Refresh Middleware ← Exponential Backoff Middleware ← HTTP Response
  ```
- **Thread-Safe Authentication**: Uses `asyncio.Lock()` with a double-check pattern to prevent concurrent token refresh attempts.

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `aiohttp` | Async HTTP client framework |
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

## 3. Home Assistant Integration Compatibility

This SDK is a dependency of the [myconso_ha](https://github.com/remijouannet/myconso_ha) Home Assistant custom integration. Because Home Assistant runs in a single, tightly controlled Python environment, **this SDK must always remain compatible with Home Assistant's own dependency tree**.

### Rules for Adding or Updating Dependencies

1. **Check Home Assistant constraints first** — Before bumping any dependency, compare the desired version against Home Assistant's `package_constraints.txt` for the target Home Assistant release used by `myconso_ha`.
2. **Never require a version higher than Home Assistant's pin** — If Home Assistant pins a package to a specific version, the SDK must allow that exact version or a compatible range that includes it.
3. **Avoid pinning exact versions for shared packages** — Do not use `==` for packages that Home Assistant also manages. Use compatible lower bounds (e.g., `>=`) that remain within Home Assistant's allowed range.
4. **Prefer Home Assistant's built-in dependencies** — Only introduce new third-party packages if they are strictly necessary and do not collide with packages already bundled by Home Assistant.
5. **Test compatibility in the integration context** — After any dependency change in this SDK, validate that `myconso_ha` still installs correctly and passes its tests inside a Home Assistant environment.

---

## 4. Standards & Tooling

This project uses `uv` for package management, `ruff` for linting/formatting, `mypy` for type checking, and `pre-commit` for git hooks. Configuration lives in `pyproject.toml` and `.pre-commit-config.yaml`.

Expect modern Python 3.10+ syntax: union types (`X | Y`), type annotations on all public APIs, and async-first patterns throughout.

---

## 5. Agentic Workflows

### Adding a New API Endpoint

1. Add the method in `myconso/api.py` using the `@check_auth` decorator and full type hints.
2. Add tests in `tests/test_api.py`.
3. Run linting and type checking:
   ```bash
   uv run ruff check myconso/api.py
   uv run mypy myconso/api.py
   ```

### Adding Middleware

1. Create the middleware function in `myconso/middlewares.py`.
2. Register it in `MyConsoClient.__init__` by appending to the `middlewares` list.

### Updating Public APIs

1. Ensure docstrings follow Google/NumPy style.
2. Update CLI help text in `myconso/cli.py` if the change is user-facing.
3. Update `README.md` with new features.

---

## 6. Testing

**Do not run integration tests unless `MYCONSO_EMAIL`, `MYCONSO_PASSWORD`, and `MYCONSO_HOUSING` are set.**

| Variable | Description |
|----------|-------------|
| `MYCONSO_EMAIL` | Account email |
| `MYCONSO_PASSWORD` | Account password |
| `MYCONSO_HOUSING` | Housing ID for testing |

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_backoff.py

# Run only mocked tests (no API calls)
uv run pytest tests/test_backoff.py tests/test_refresh_token.py
```

---

## 7. Quick Reference

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

**Last Updated**: 2026-05-02
**Agent Note**: When modifying this SDK, maintain async-first patterns, use type hints, ensure all tests pass with `uv run pytest`, and verify that dependency changes remain compatible with Home Assistant's pinned versions.
