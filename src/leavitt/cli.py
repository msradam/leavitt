"""Leavitt CLI.

    leavitt serve                 run the MCP server (stdio) for an MCP client
    leavitt graph                 print the FSM topology

The investigation entrypoint lands in a later phase; for now ``serve`` exposes
the Theodosia ``step`` surface and ``graph`` prints the enforced transitions.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="leavitt", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="run the Theodosia MCP server over stdio")
    sub.add_parser("graph", help="print the FSM topology")
    args = parser.parse_args()

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
