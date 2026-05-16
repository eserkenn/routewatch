"""Renders route summaries as formatted text tables for CLI/log output."""

from dataclasses import dataclass
from typing import List, Protocol


class HasUrlAndMetrics(Protocol):
    url: str
    success_rate: float
    failure_rate: float
    average_latency_ms: float
    consecutive_failures: int


@dataclass
class RenderedTable:
    header: str
    rows: List[str]
    footer: str

    def as_text(self) -> str:
        lines = [self.header] + self.rows + [self.footer]
        return "\n".join(lines)


_COL_WIDTHS = {
    "url": 40,
    "success": 10,
    "latency": 14,
    "consec_fail": 13,
}

_HEADER_LABELS = {
    "url": "URL",
    "success": "SUCCESS %",
    "latency": "AVG LATENCY",
    "consec_fail": "CONSEC FAIL",
}


def _separator() -> str:
    parts = [("-" * w) for w in _COL_WIDTHS.values()]
    return "+" + "+".join(parts) + "+"


def _header_row() -> str:
    cells = [
        label.center(w)
        for label, w in zip(_HEADER_LABELS.values(), _COL_WIDTHS.values())
    ]
    return "|" + "|".join(cells) + "|"


def _format_row(route: HasUrlAndMetrics) -> str:
    url_cell = route.url[: _COL_WIDTHS["url"]].ljust(_COL_WIDTHS["url"])
    success_cell = f"{route.success_rate * 100:.1f}%".rjust(_COL_WIDTHS["success"])
    latency_cell = f"{route.average_latency_ms:.1f} ms".rjust(_COL_WIDTHS["latency"])
    consec_cell = str(route.consecutive_failures).rjust(_COL_WIDTHS["consec_fail"])
    return f"|{url_cell}|{success_cell}|{latency_cell}|{consec_cell}|"


def render_routes(routes: List[HasUrlAndMetrics]) -> RenderedTable:
    """Build a RenderedTable from a list of route metric objects."""
    sep = _separator()
    header = "\n".join([sep, _header_row(), sep])
    rows = [_format_row(r) for r in routes]
    total = len(routes)
    healthy = sum(1 for r in routes if r.consecutive_failures == 0)
    footer = "\n".join([sep, f"  {healthy}/{total} routes healthy"])
    return RenderedTable(header=header, rows=rows, footer=footer)
