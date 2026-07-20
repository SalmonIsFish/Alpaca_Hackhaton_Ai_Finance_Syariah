"""Read one market snapshot through OpenD. No trading account or order API is used."""

import argparse
import sys

try:
    from moomoo import OpenQuoteContext
except ModuleNotFoundError as exc:  # pragma: no cover - environment check
    print("Moomoo SDK is not installed in this Python environment.")
    print("Install it with: python -m pip install moomoo-api")
    raise SystemExit(3) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Moomoo quote check")
    parser.add_argument("code", help="Moomoo symbol, for example US.AAPL or HK.00700")
    args = parser.parse_args()

    quote = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        ret, data = quote.get_market_snapshot([args.code])
        if ret != 0:
            print(f"Quote request failed: {ret}")
            return 1
        print("READ-ONLY QUOTE VERIFIED")
        print(data.to_string(index=False))
        print("No trading account was selected. No order was submitted.")
        return 0
    finally:
        quote.close()


if __name__ == "__main__":
    sys.exit(main())
