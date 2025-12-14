
# Async Python client for myconso (proxiserve) API

A fully asynchronous API client for the myconso API behind the [Myconso APP](https://play.google.com/store/apps/details?id=fr.proxiserve.myconso&hl=fr). To easily retrive information about your 

## Installation

```bash
pip install myconso 
```

## Getting started


```python
import asyncio
import time

from pyoverkiz.const import SUPPORTED_SERVERS
from pyoverkiz.client import OverkizClient
from pyoverkiz.enums import Server

USERNAME = ""
PASSWORD = ""


async def main() -> None:
    async with OverkizClient(
        USERNAME, PASSWORD, server=SUPPORTED_SERVERS[Server.SOMFY_EUROPE]
    ) as client:
        try:
            await client.login()
        except Exception as exception:  # pylint: disable=broad-except
            print(exception)
            return

        devices = await client.get_devices()

        for device in devices:
            print(f"{device.label} ({device.id}) - {device.controllable_name}")
            print(f"{device.widget} - {device.ui_class}")

        while True:
            events = await client.fetch_events()
            print(events)

            time.sleep(2)


asyncio.run(main())
```


## Projects using pyOverkiz

This package powers the Overkiz integration in [Home Assistant Core](https://www.home-assistant.io/integrations/overkiz/). Other open-source projects and custom automations also leverage pyOverkiz to interact with Overkiz-compatible hubs and devices, including:

- [overkiz2mqtt](https://github.com/RichieB2B/overkiz2mqtt): Bridges Overkiz devices to MQTT for integration with various platforms.
- [mcp-overkiz](https://github.com/phimage/mcp-overkiz): Implements an MCP server to enable communication between Overkiz devices and language models.
- [tahoma](https://github.com/pzim-devdata/tahoma): Command Line Interface (CLI) to control Overkiz devices.


## Contribute

We welcome contributions! To get started with setting up this project for development, follow the steps below.

### Dev Container (recommended)

If you use Visual Studio Code with Docker or GitHub Codespaces, you can take advantage of the included [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers). This environment comes pre-configured with all necessary dependencies and tools, including the correct Python version, making setup simple and straightforward.

### Manual

- Ensure Python 3.12 is installed on your system.
- Install [uv](https://docs.astral.sh/uv/getting-started/installation).
- Clone this repository and navigate to it: `cd python-overkiz-api`
- Initialize the project with `uv sync`, then run `uv run pre-commit install`

