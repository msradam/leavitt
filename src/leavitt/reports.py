"""Structured incident triage report.

``disposition`` is constrained by evidence, not by the LLM's confidence.
``produce_report`` refuses ``resolved`` when no source was usable; the report
carries that constraint so the audit trail shows why a run concluded the way
it did.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

RESOLVED = "resolved"
DEGRADED = "degraded"
INCONCLUSIVE = "inconclusive"


@dataclass
class TriageReport:
    query: str
    disposition: str
    confidence: str
    root_cause: str
    affected_services: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    sources_queried: list[str] = field(default_factory=list)
    sources_usable: list[str] = field(default_factory=list)
    sources_failed: list[dict[str, str]] = field(default_factory=list)
    recovery_events: list[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def render(self) -> str:
        lines = [
            f"Incident triage: {self.query}",
            f"  disposition:        {self.disposition}",
            f"  confidence:         {self.confidence}",
            f"  root cause:         {self.root_cause}",
            f"  affected services:  {', '.join(self.affected_services) or '(none identified)'}",
            f"  sources usable:     {len(self.sources_usable)}/{len(self.sources_queried)} "
            f"({', '.join(self.sources_usable) or 'none'})",
        ]
        if self.sources_failed:
            for f in self.sources_failed:
                lines.append(f"  source failed:      {f['name']} -> {f['detail']}")
        if self.recovery_events:
            for ev in self.recovery_events:
                lines.append(f"  recovery:           {ev}")
        if self.evidence:
            lines.append("  evidence:")
            for e in self.evidence:
                lines.append(f"    - [{e.get('source')}] {e.get('summary')}")
        return "\n".join(lines)
