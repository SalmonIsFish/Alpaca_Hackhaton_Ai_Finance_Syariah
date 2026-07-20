"""Check Moomoo OpenD paper-account status without submitting orders."""

from moomoo_status import check_moomoo_status


def main() -> int:
    status = check_moomoo_status()
    print(f"Status: {status['status']}")
    print(f"Host: {status['host']}")
    print(f"Port: {status['port']}")
    print(f"Mode: {status['mode']}")
    print(f"Paper account ready: {status['paper_account_ready']}")
    print(f"Broker submission: {status['broker_submission']}")
    if status.get("environment"):
        print(f"Environment: {status['environment']}")
    if status.get("account_type"):
        print(f"Account type: {status['account_type']}")
    if status.get("account_status"):
        print(f"Account status: {status['account_status']}")
    if status.get("account_suffix"):
        print(f"Account suffix: ...{status['account_suffix']}")
    if status.get("reason"):
        print(f"Reason: {status['reason']}")
    return 0 if status["paper_account_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
