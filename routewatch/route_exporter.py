"""Export route check results and metrics to various formats (JSON, CSV)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import List, Sequence

from routewatch.logging_config import get_logger
from routewatch.metrics import MetricsCollector
from routewatch.status import build_status_report
from routewatch.history import LatencyHistory

logger = get_logger(__name__)


@dataclass
class ExportRow:
    route_url: str
    method: str
    success_rate: float
    failure_rate: float
    consecutive_failures: int
    avg_latency_ms: float
    healthy: bool


def build_export_rows(
    collector: MetricsCollector,
    history: LatencyHistory,
    failure_threshold: int = 3,
) -> List[ExportRow]:
    """Build a list of ExportRow objects from current metrics and history."""
    report = build_status_report(collector, history, failure_threshold)
    rows: List[ExportRow] = []
    for summary in report.routes:
        metrics = collector.get(summary.url)
        rows.append(
            ExportRow(
                route_url=summary.url,
                method=summary.method,
                success_rate=round(metrics.success_rate(), 4),
                failure_rate=round(metrics.failure_rate(), 4),
                consecutive_failures=metrics.consecutive_failures,
                avg_latency_ms=round(summary.avg_latency_ms, 2),
                healthy=summary.healthy,
            )
        )
    return rows


def export_json(rows: Sequence[ExportRow]) -> str:
    """Serialize export rows to a JSON string."""
    data = [asdict(r) for r in rows]
    return json.dumps(data, indent=2)


def export_csv(rows: Sequence[ExportRow]) -> str:
    """Serialize export rows to a CSV string."""
    if not rows:
        return ""
    output = io.StringIO()
    fieldnames = list(asdict(rows[0]).keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(asdict(row))
    return output.getvalue()
