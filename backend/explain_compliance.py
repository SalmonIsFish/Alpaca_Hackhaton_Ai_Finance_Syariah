"""Combine an external screening result with local policy context."""

import argparse

from wiki_context import find_policy_context
from zoya_compliance import check_us_symbol


parser = argparse.ArgumentParser()
parser.add_argument("symbol")
args = parser.parse_args()

result = check_us_symbol(args.symbol)
context = find_policy_context(f"{args.symbol} Shariah compliance screening policy")
print({"screening": result, "policy_context": context, "decision_rule": "External NON_COMPLIANT, ERROR, or NOT_CONFIGURED results remain rejected; wiki notes explain but cannot override."})
