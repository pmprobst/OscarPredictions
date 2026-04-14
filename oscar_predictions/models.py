"""Shared dataclasses for sync orchestration and stage reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageSummary:
    """Structured summary for one pipeline stage."""

    name: str
    ran: bool
    skipped: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncReport:
    """Aggregate report returned by ``run_sync``."""

    stage_summaries: list[StageSummary] = field(default_factory=list)
    upstream_changed: bool = False
    dry_run: bool = False
