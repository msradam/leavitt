"""Classify upstream MCP responses so a single bad source never poisons correlation.

Every query action routes its ``call_upstream`` through ``safe_upstream``. The
wrapper never raises. It returns a ``SourceResult`` tagged ``ok``, ``error``, or
``malformed`` so ``correlate_evidence`` can count coverage and mark the report's
confidence without inspecting raw exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from theodosia import UpstreamError, call_upstream

OK = "ok"
ERROR = "error"
MALFORMED = "malformed"


@dataclass
class SourceResult:
    name: str
    status: str
    data: Any = None
    detail: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status == OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "data": self.data,
            "detail": self.detail,
            "meta": self.meta,
        }


def classify_payload(name: str, payload: Any, *, expect: str) -> SourceResult:
    """Decide whether a returned payload is usable.

    ``expect`` is one of ``"list"``, ``"dict"``, or ``"any"``. A response of the
    wrong shape, or an MCP-level error string, is ``malformed`` rather than
    ``ok`` so it is excluded from correlation.
    """
    if payload is None:
        return SourceResult(name, ERROR, detail="empty response")
    if isinstance(payload, str):
        low = payload.lower()
        if any(t in low for t in ("error", "exception", "traceback", "failed")):
            return SourceResult(name, ERROR, detail=payload[:300])
        return SourceResult(name, MALFORMED, data=payload, detail="unstructured text")
    if isinstance(payload, dict) and payload.get("error"):
        return SourceResult(name, ERROR, detail=str(payload.get("error"))[:300])
    if expect == "list" and not isinstance(payload, (list, dict)):
        return SourceResult(name, MALFORMED, data=payload, detail="expected list/dict")
    if expect == "dict" and not isinstance(payload, dict):
        return SourceResult(name, MALFORMED, data=payload, detail="expected dict")
    return SourceResult(name, OK, data=payload)


async def safe_upstream(
    name: str, server: str, tool: str, args: dict[str, Any], *, expect: str = "any"
) -> SourceResult:
    """Call an upstream tool and return a classified result. Never raises."""
    try:
        payload = await call_upstream(server, tool, args or {})
    except UpstreamError as exc:
        return SourceResult(name, ERROR, detail=f"upstream unavailable: {exc}"[:300])
    except Exception as exc:  # noqa: BLE001 - any upstream/transport failure is a source error, not a crash
        return SourceResult(name, ERROR, detail=f"{type(exc).__name__}: {exc}"[:300])
    return classify_payload(name, payload, expect=expect)


def coverage(results: list[SourceResult]) -> tuple[int, int]:
    """Return ``(usable_sources, configured_sources)``."""
    return sum(1 for r in results if r.usable), len(results)


def confidence_label(usable: int, total: int) -> str:
    if total == 0 or usable == 0:
        return "none"
    if usable < total:
        return "degraded"
    return "full"
