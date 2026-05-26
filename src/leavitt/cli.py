"""Leavitt CLI.

leavitt investigate "<question>"  run a triage with a live terminal view
leavitt serve                     run the MCP server (stdio) for an MCP client
leavitt graph                     print the FSM topology
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="leavitt", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")
    inv = sub.add_parser("investigate", help="run a triage with a live terminal view")
    inv.add_argument("query", help="the incident question")
    agt = sub.add_parser(
        "agent", help="drive a headless Hermes/Nemotron run and render it live"
    )
    agt.add_argument("query", help="the incident question")
    ses = sub.add_parser("sessions", help="list past FSM sessions (the audit trail)")
    ses.add_argument("id", nargs="?", help="a session id prefix to show in full")
    sub.add_parser("serve", help="run the Theodosia MCP server over stdio")
    sub.add_parser("graph", help="print the FSM topology")
    args = parser.parse_args()

    if args.cmd == "investigate":
        from leavitt.tui import run

        return run(args.query)

    if args.cmd == "agent":
        from leavitt.tui import run_agent

        return run_agent(args.query)

    if args.cmd == "sessions":
        from leavitt.sessions import list_sessions, show_session

        return show_session(args.id) if args.id else list_sessions()

    if args.cmd == "graph":
        from leavitt.app import build_application

        app = build_application(track=False)
        print("Leavitt FSM actions:")
        for a in app.graph.actions:
            print(f"  - {a.name}  reads={list(a.reads)} writes={list(a.writes)}")
        print("\nTransitions:")
        for t in app.graph.transitions:
            cond = getattr(t.condition, "name", "default")
            print(f"  {t.from_.name} -> {t.to.name}  [{cond}]")
        return 0

    if args.cmd == "serve":
        from leavitt.app import mount_server

        mount_server().run()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
