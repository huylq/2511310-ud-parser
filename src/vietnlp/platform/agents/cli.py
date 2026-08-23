"""Operator CLI for the agent layer: `python -m vietnlp.platform.agents.cli ...`"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

from .budget import BudgetExceeded, BudgetLedger
from .cache import ResponseCache
from .policy import Model, all_tasks, estimate_usd, route
from .registry import AGENTS, ValidationFailed, get


def cmd_routes(_args) -> int:
    print(f"{'TASK':<24} {'MODEL':<18} {'MAX_OUT':>8} {'BATCH':>6}  RATIONALE")
    for task in all_tasks():
        r = route(task)
        print(f"{r.task:<24} {r.model.value:<18} {r.max_output_tokens:>8} {r.batch_size:>6}  {r.rationale}")
    return 0


def cmd_agents(_args) -> int:
    for name, agent in sorted(AGENTS.items()):
        r = agent.route
        print(f"{name:<22} {r.model.value:<18} prompt={agent.prompt_version:<5} {agent.description}")
    return 0


def cmd_estimate(args) -> int:
    """What would N calls of this task cost? Run this before starting a flow."""
    r = route(args.task)
    per_call = estimate_usd(r.model, args.input_tokens, r.max_output_tokens)
    calls = max(1, args.count // max(1, r.batch_size))
    total = per_call * calls
    print(f"task            {r.task}")
    print(f"model           {r.model.value}")
    print(f"items           {args.count} (batch {r.batch_size} -> {calls} calls)")
    print(f"per call        ${per_call:.6f}")
    print(f"total (no cache) ${total:.2f}")
    print(f"at 60% cache hit ${total * 0.4:.2f}")
    return 0


def cmd_spend(args) -> int:
    ledger = BudgetLedger()
    rows = ledger.report(args.flow_run_id)
    if not rows:
        print("no spend recorded")
        return 0
    print(f"{'TASK':<24} {'MODEL':<18} {'CALLS':>6} {'IN':>10} {'CACHED':>10} {'OUT':>10} {'USD':>10}")
    total = 0.0
    for task, model, calls, tin, tcached, tout, usd in rows:
        print(f"{task:<24} {model:<18} {calls:>6} {tin:>10} {tcached:>10} {tout:>10} {usd:>10.4f}")
        total += usd
    print(f"{'TOTAL':<24} {'':<18} {'':>6} {'':>10} {'':>10} {'':>10} {total:>10.4f}")
    s = ledger.spent(args.flow_run_id or "")
    print(f"\ncaps: flow ${ledger.flow_cap:.2f} | daily ${ledger.daily_cap:.2f} "
          f"(used ${s.day_usd:.4f}) | total ${ledger.total_cap:.2f} (used ${s.total_usd:.4f})")
    return 0


def cmd_cache(args) -> int:
    cache = ResponseCache()
    if args.invalidate:
        n = cache.invalidate(args.invalidate, args.prompt_version)
        print(f"invalidated {n} entries for task={args.invalidate}")
        return 0
    rows = cache.stats()
    if not rows:
        print("cache empty")
        return 0
    print(f"{'TASK':<24} {'PROMPT':<8} {'ENTRIES':>8} {'HITS':>8}")
    for task, ver, entries, hits in rows:
        print(f"{task:<24} {ver:<8} {entries:>8} {hits or 0:>8}")
    return 0


def cmd_run(args) -> int:
    """Run one agent against text on stdin. For smoke-testing a deployment."""
    from .client import AgentClient

    agent = get(args.agent)
    text = args.text or sys.stdin.read()
    if not text.strip():
        print("error: no input text", file=sys.stderr)
        return 2
    flow_run_id = os.getenv("VIETNLP_FLOW_RUN_ID") or f"cli-{uuid.uuid4().hex[:8]}"
    with AgentClient(flow_run_id=flow_run_id) as client:
        try:
            validated, result = agent.run(client, text)
        except BudgetExceeded as exc:
            print(f"BUDGET STOP: {exc}", file=sys.stderr)
            return 3
        except ValidationFailed as exc:
            # Rule 4: no silent drops. In a flow this goes to the dead-letter
            # partition; on the CLI it goes to stderr with a non-zero exit.
            print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
            return 4
    print(json.dumps(validated, ensure_ascii=False, indent=2))
    print(
        f"\n[{result.model} | {'cache hit' if result.cached else f'${result.usd:.6f}'} "
        f"| in={result.input_tokens} cached={result.cached_tokens} out={result.output_tokens}]",
        file=sys.stderr,
    )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="vietnlp-agents", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("routes", help="show the task -> model cost table").set_defaults(fn=cmd_routes)
    sub.add_parser("agents", help="list registered sub-agents").set_defaults(fn=cmd_agents)

    p = sub.add_parser("estimate", help="estimate cost of a task before running it")
    p.add_argument("task", choices=all_tasks())
    p.add_argument("--count", type=int, default=1000, help="number of items")
    p.add_argument("--input-tokens", type=int, default=500, help="tokens per item")
    p.set_defaults(fn=cmd_estimate)

    p = sub.add_parser("spend", help="report recorded spend")
    p.add_argument("--flow-run-id", default=None)
    p.set_defaults(fn=cmd_spend)

    p = sub.add_parser("cache", help="cache stats, or invalidate a task")
    p.add_argument("--invalidate", metavar="TASK")
    p.add_argument("--prompt-version", default=None)
    p.set_defaults(fn=cmd_cache)

    p = sub.add_parser("run", help="run one agent on text (smoke test)")
    p.add_argument("agent", choices=sorted(AGENTS))
    p.add_argument("--text", default=None, help="text to process; default stdin")
    p.set_defaults(fn=cmd_run)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
