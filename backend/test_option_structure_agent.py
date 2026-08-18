"""Verify the option-structure agent normalizes the gate result correctly."""

from agents.option_structure_agent import evaluate_option_structure


def main() -> None:
    passed = evaluate_option_structure(structure="covered_call", shares_held=100, contracts=1)
    assert passed["agent"] == "option_structure"
    assert passed["status"] == "PASS"
    assert passed["reason"] == "covered_by_owned_shares"
    assert passed["details"]["structure"] == "covered_call"

    rejected = evaluate_option_structure(structure="naked_call")
    assert rejected["agent"] == "option_structure"
    assert rejected["status"] == "REJECT"
    assert rejected["reason"] == "structure_not_permitted"

    print("PASS: option structure agent normalizes gate results.")


if __name__ == "__main__":
    main()
