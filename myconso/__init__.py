import importlib.metadata

from myconso.api import MyConsoClient

try:
    __version__ = importlib.metadata.version("myconso")  # the [project] name
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for an uninstalled source tree

__all__ = ["MyConsoClient"]
