"""CLI: explain one symbol's Shariah verdict, with the rule and citations.

The command-line view of GET /stock/{symbol}/explain. Both go through
shariah_explain.explain_symbol, so the CLI and the dashboard can never disagree
about the same company -- NEXT_STEPS.md's "one screening record, two views".

This previously called zoya_compliance.check_us_symbol directly, which made it a
third screening path (alongside the API and us_strategy.py) to a provider the API
no longer uses at all.

Local policy notes are still attached, under the same rule as before: notes
explain but cannot override.
"""

import argparse
import json

from shariah_explain import explain_symbol
from wiki_context import find_policy_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("symbol")
    parser.add_argument("--json", action="store_true", help="print the raw /explain payload")
    parser.add_argument("--no-notes", action="store_true", help="skip the local policy-note lookup")
    args = parser.parse_args()

    payload = explain_symbol(args.symbol)

    if not args.no_notes:
        payload["policy_context"] = find_policy_context(
            f"{args.symbol} Shariah compliance screening policy"
        )

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    verdict = payload["verdict"]
    rule = payload["rule"] or {}
    print(f"{payload['symbol']}  {payload.get('company') or ''}".strip())
    print(f"  verdict:   {verdict['status']}  (tradeable={verdict['tradeable']})")
    print(f"  statement: {verdict['statement']}")
    print(f"  rule:      {rule.get('label')} [{rule.get('id')}]")

    for test in rule.get("tests") or []:
        mark = "pass" if test["passed"] else "FAIL"
        print(
            f"    - {mark}  {test['label']}: "
            f"{test['value_pct']:.2f}% {test['comparator']} {test['limit_pct']:.0f}% "
            f"(margin {test['margin_pct']:+.2f} pts)"
        )

    print("  fiqh basis:")
    for entry in payload["fiqh_basis"]:
        citation = entry["citation"]
        print(f"    - {entry['principle']}: {entry['claim']}")
        print(f"      cite: {citation['source']} [{citation['kind']}]")

    print("  limitations:")
    for limitation in payload["provenance"]["limitations"]:
        print(f"    - {limitation}")

    print(f"  decision rule: {payload['decision_rule']}")


if __name__ == "__main__":
    main()
