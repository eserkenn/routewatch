"""Attach and resolve arbitrary key-value labels to routes for richer filtering and reporting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Protocol


class HasUrlAndLabels(Protocol):
    url: str
    labels: Dict[str, str]


@dataclass
class LabelSelector:
    """Match routes whose labels satisfy ALL provided key=value pairs."""

    required: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "LabelSelector":
        return cls(required=dict(d))

    def matches(self, labels: Dict[str, str]) -> bool:
        """Return True when every required pair is present in *labels*."""
        return all(labels.get(k) == v for k, v in self.required.items())


class RouteLabelIndex:
    """Maintains a fast lookup from label key/value pairs to route URLs."""

    def __init__(self) -> None:
        # {key: {value: [url, ...]}}
        self._index: Dict[str, Dict[str, List[str]]] = {}

    def index_route(self, url: str, labels: Dict[str, str]) -> None:
        """Register *url* under each of its label pairs."""
        for k, v in labels.items():
            self._index.setdefault(k, {}).setdefault(v, []).append(url)

    def lookup(self, key: str, value: str) -> List[str]:
        """Return URLs that carry the label *key=value*."""
        return list(self._index.get(key, {}).get(value, []))

    def all_values(self, key: str) -> List[str]:
        """Return every distinct value seen for *key*."""
        return list(self._index.get(key, {}).keys())


def filter_by_selector(
    routes: Iterable[HasUrlAndLabels],
    selector: Optional[LabelSelector],
) -> List[HasUrlAndLabels]:
    """Return routes matched by *selector*; returns all routes when selector is None."""
    if selector is None or not selector.required:
        return list(routes)
    return [r for r in routes if selector.matches(r.labels)]
