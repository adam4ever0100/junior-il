"""Source registry."""
from junior_il.sources.base import Source, fetch_json
from junior_il.sources.comeet import ComeetSource
from junior_il.sources.greenhouse import GreenhouseSource

SOURCES: dict[str, type] = {
    GreenhouseSource.name: GreenhouseSource,
    ComeetSource.name: ComeetSource,
}

__all__ = ["Source", "fetch_json", "GreenhouseSource", "ComeetSource", "SOURCES"]
