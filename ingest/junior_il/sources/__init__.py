"""Source registry."""
from junior_il.sources.base import Source
from junior_il.sources.greenhouse import GreenhouseSource

SOURCES: dict[str, type] = {
    GreenhouseSource.name: GreenhouseSource,
}

__all__ = ["Source", "GreenhouseSource", "SOURCES"]
