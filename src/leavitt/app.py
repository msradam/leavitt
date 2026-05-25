"""The Leavitt Burr Application and its Theodosia mount.

The FSM is linear with one recovery branch:

    receive_query -> enumerate_sources -> query_grafana_metrics
      -> query_grafana_logs -> query_deployment_context -> correlate_evidence
    correlate_evidence -> query_grafana_metrics   (when should_retry: total source failure)
    correlate_evidence -> form_hypothesis          (otherwise)
    form_hypothesis -> produce_report              (terminal)

Theodosia enforces these edges. An agent cannot step from ``receive_query`` to
``produce_report``; ``correlate_evidence`` cannot be skipped. Every action is
READ-class. There is no write action and no ``unlock_readwrite`` edge, so the
read-only posture is structural, not a runtime flag.
"""

from __future__ import annotations

import os
from typing import Any

from burr.core import ApplicationBuilder, Application, default, when

import theodosia
from leavitt import actions

_INITIAL_STATE: dict[str, Any] = {
    "query": "",
    "max_retries": 1,
    "retry_count": 0,
    "recovery_events": [],
    "mode": "readonly",
    "sources": [],
    "metrics_result": None,
    "logs_result": None,
    "deployment_result": None,
    "evidence": [],
    "usable_count": 0,
    "source_count": 0,
    "confidence": "none",
    "should_retry": False,
    "root_cause": "undetermined",
    "affected_services": [],
    "hypothesis": "",
    "report": None,
    "disposition": "",
}


def build_application(app_id: str | None = None, track: bool = True) -> Application:
    builder = (
        ApplicationBuilder()
        .with_actions(
            receive_query=actions.receive_query,
            enumerate_sources=actions.enumerate_sources,
            query_grafana_metrics=actions.query_grafana_metrics,
            query_grafana_logs=actions.query_grafana_logs,
            query_deployment_context=actions.query_deployment_context,
            correlate_evidence=actions.correlate_evidence,
            form_hypothesis=actions.form_hypothesis,
            produce_report=actions.produce_report,
        )
        .with_transitions(
            ("receive_query", "enumerate_sources"),
            ("enumerate_sources", "query_grafana_metrics"),
            ("query_grafana_metrics", "query_grafana_logs"),
            ("query_grafana_logs", "query_deployment_context"),
            ("query_deployment_context", "correlate_evidence"),
            ("correlate_evidence", "query_grafana_metrics", when(should_retry=True)),
            ("correlate_evidence", "form_hypothesis", default),
            ("form_hypothesis", "produce_report"),
        )
        .with_state(**_INITIAL_STATE)
        .with_entrypoint("receive_query")
    )
    if track:
        builder = builder.with_tracker(theodosia.tracker("leavitt"))
    if app_id:
        builder = builder.with_identifiers(app_id=app_id)
    return builder.build()


def default_upstream() -> dict[str, Any]:
    """Upstream MCP server transports. Override via env for real deployments."""
    grafana = os.getenv("LEAVITT_GRAFANA_MCP", "http://localhost:8000/mcp")
    flagctx = os.getenv("LEAVITT_FLAGCTX_MCP")
    cfg: dict[str, Any] = {"grafana": grafana}
    if flagctx:
        cfg["flagctx"] = flagctx
    return cfg


def mount_server(upstream: dict[str, Any] | None = None):
    """Return a FastMCP server exposing Leavitt's ``step`` surface."""
    return theodosia.mount(
        lambda: build_application(),
        name="leavitt",
        instructions=(
            "Leavitt is a read-only observability triage agent. Drive it with the "
            "step tool following the enforced FSM. It reads Grafana metrics and logs "
            "and deployment context, correlates them, then produces a triage report. "
            "It cannot run commands or modify anything."
        ),
        upstream=upstream if upstream is not None else default_upstream(),
    )
